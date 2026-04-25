use std::collections::BTreeMap;
use std::fs::File;
use std::path::Path;
use std::sync::mpsc::sync_channel;
use std::sync::Arc;
use std::thread;

use anyhow::{bail, Context, Result};
use arrow_array::{ArrayRef, Int32Array, Int64Array, RecordBatch, StringArray};
use arrow_schema::{DataType, Field, Schema};
use memmap2::MmapOptions;
use parquet::arrow::ArrowWriter;
use rayon::prelude::*;
use parquet::basic::{Compression, ZstdLevel};
use parquet::file::properties::WriterProperties;
use pyo3::exceptions::PyRuntimeError;
use pyo3::prelude::*;
use regex::Regex;

#[derive(Debug, Clone, Copy)]
pub enum ParquetCompression {
    Zstd,
    Snappy,
    Uncompressed,
}

impl ParquetCompression {
    pub fn from_str(raw: &str) -> Result<Self> {
        match raw.to_ascii_lowercase().as_str() {
            "zstd" => Ok(Self::Zstd),
            "snappy" => Ok(Self::Snappy),
            "uncompressed" | "none" => Ok(Self::Uncompressed),
            _ => bail!("Unsupported compression '{raw}'. Use zstd|snappy|uncompressed."),
        }
    }
}

#[derive(Debug, Clone)]
enum CobolType {
    Alpha(usize),
    Numeric(usize),
    NumericImplied { int_digits: usize, frac_digits: usize },
}

#[derive(Debug, Clone)]
struct FieldSpec {
    name: String,
    kind: CobolType,
    offset: usize,
}

impl FieldSpec {
    fn width(&self) -> usize {
        match self.kind {
            CobolType::Alpha(w) => w,
            CobolType::Numeric(w) => w,
            CobolType::NumericImplied {
                int_digits,
                frac_digits,
            } => int_digits + frac_digits,
        }
    }
}

trait NamedType {
    fn map_with_name(self, name: String) -> Option<(String, CobolType)>;
}

impl NamedType for CobolType {
    fn map_with_name(self, name: String) -> Option<(String, CobolType)> {
        Some((name, self))
    }
}

fn parse_copybook(copybook_text: &str) -> Result<Vec<FieldSpec>> {
    let alpha_re = Regex::new(r"(?i)^\s*\d+\s+([A-Z0-9_-]+)\s+PIC\s+A\((\d+)\)\s*[.,]?\s*$")?;
    let num_re = Regex::new(r"(?i)^\s*\d+\s+([A-Z0-9_-]+)\s+PIC\s+9\((\d+)\)\s*[.,]?\s*$")?;
    let num_v_re = Regex::new(
        r"(?i)^\s*\d+\s+([A-Z0-9_-]+)\s+PIC\s+9\((\d+)\)\s*V\s*9\((\d+)\)\s*[.,]?\s*$",
    )?;
    let num_v_plain_re =
        Regex::new(r"(?i)^\s*\d+\s+([A-Z0-9_-]+)\s+PIC\s+9\((\d+)\)\s*V\s*(9+)\s*[.,]?\s*$")?;

    let mut specs = Vec::new();
    let mut offset = 0usize;

    for raw_line in copybook_text.lines() {
        let line = raw_line.trim();
        if line.is_empty() || line.starts_with('*') {
            continue;
        }

        let parsed = if let Some(cap) = alpha_re.captures(line) {
            let name = cap[1].to_string();
            let w: usize = cap[2].parse().context("Invalid A(n) width")?;
            CobolType::Alpha(w).map_with_name(name)
        } else if let Some(cap) = num_v_re.captures(line) {
            let name = cap[1].to_string();
            let int_digits: usize = cap[2].parse().context("Invalid 9(n) integer width")?;
            let frac_digits: usize = cap[3].parse().context("Invalid 9(m) fraction width")?;
            CobolType::NumericImplied {
                int_digits,
                frac_digits,
            }
            .map_with_name(name)
        } else if let Some(cap) = num_v_plain_re.captures(line) {
            let name = cap[1].to_string();
            let int_digits: usize = cap[2].parse().context("Invalid 9(n) integer width")?;
            let frac_digits: usize = cap[3].len();
            CobolType::NumericImplied {
                int_digits,
                frac_digits,
            }
            .map_with_name(name)
        } else if let Some(cap) = num_re.captures(line) {
            let name = cap[1].to_string();
            let w: usize = cap[2].parse().context("Invalid 9(n) width")?;
            CobolType::Numeric(w).map_with_name(name)
        } else {
            None
        };

        if let Some((name, kind)) = parsed {
            let spec = FieldSpec { name, kind, offset };
            offset += spec.width();
            specs.push(spec);
        }
    }

    if specs.is_empty() {
        bail!("No supported PIC fields found in copybook.");
    }
    Ok(specs)
}

fn schema_for_specs(specs: &[FieldSpec]) -> Arc<Schema> {
    let fields: Vec<Field> = specs
        .iter()
        .map(|spec| {
            let dtype = match spec.kind {
                CobolType::Alpha(_) => DataType::Utf8,
                CobolType::Numeric(_) => DataType::Int32,
                CobolType::NumericImplied { .. } => DataType::Int64,
            };
            Field::new(spec.name.clone(), dtype, false)
        })
        .collect();
    Arc::new(Schema::new(fields))
}

fn parse_ascii_i32(bytes: &[u8]) -> Result<i32> {
    let s = std::str::from_utf8(bytes)?.trim();
    Ok(if s.is_empty() { 0 } else { s.parse::<i32>()? })
}

fn parse_ascii_i64(bytes: &[u8]) -> Result<i64> {
    let s = std::str::from_utf8(bytes)?.trim();
    Ok(if s.is_empty() { 0 } else { s.parse::<i64>()? })
}

fn parse_batch(specs: &[FieldSpec], rows: &[u8], record_len: usize, nrows: usize) -> Result<RecordBatch> {
    let mut string_cols: Vec<Vec<String>> = Vec::new();
    let mut i32_cols: Vec<Vec<i32>> = Vec::new();
    let mut i64_cols: Vec<Vec<i64>> = Vec::new();

    for spec in specs {
        match spec.kind {
            CobolType::Alpha(_) => string_cols.push(Vec::with_capacity(nrows)),
            CobolType::Numeric(_) => i32_cols.push(Vec::with_capacity(nrows)),
            CobolType::NumericImplied { .. } => i64_cols.push(Vec::with_capacity(nrows)),
        }
    }

    let mut alpha_idx = 0usize;
    let mut num_idx = 0usize;
    let mut num_v_idx = 0usize;

    for row_idx in 0..nrows {
        let base = row_idx * record_len;
        for spec in specs {
            let start = base + spec.offset;
            let end = start + spec.width();
            let cell = &rows[start..end];
            match spec.kind {
                CobolType::Alpha(_) => {
                    let v = std::str::from_utf8(cell)?.trim_end().to_string();
                    string_cols[alpha_idx].push(v);
                    alpha_idx += 1;
                }
                CobolType::Numeric(_) => {
                    i32_cols[num_idx].push(parse_ascii_i32(cell)?);
                    num_idx += 1;
                }
                CobolType::NumericImplied { .. } => {
                    i64_cols[num_v_idx].push(parse_ascii_i64(cell)?);
                    num_v_idx += 1;
                }
            }
        }
        alpha_idx = 0;
        num_idx = 0;
        num_v_idx = 0;
    }

    let mut arrays: Vec<ArrayRef> = Vec::with_capacity(specs.len());
    let mut alpha_take = 0usize;
    let mut num_take = 0usize;
    let mut num_v_take = 0usize;
    for spec in specs {
        match spec.kind {
            CobolType::Alpha(_) => {
                arrays.push(Arc::new(StringArray::from(std::mem::take(
                    &mut string_cols[alpha_take],
                ))) as ArrayRef);
                alpha_take += 1;
            }
            CobolType::Numeric(_) => {
                arrays.push(Arc::new(Int32Array::from(std::mem::take(
                    &mut i32_cols[num_take],
                ))) as ArrayRef);
                num_take += 1;
            }
            CobolType::NumericImplied { .. } => {
                arrays.push(Arc::new(Int64Array::from(std::mem::take(
                    &mut i64_cols[num_v_take],
                ))) as ArrayRef);
                num_v_take += 1;
            }
        }
    }

    let schema = schema_for_specs(specs);
    Ok(RecordBatch::try_new(schema, arrays)?)
}

pub fn convert_fixed_to_parquet(
    input: &Path,
    copybook: &Path,
    output: &Path,
    line_terminated: bool,
    batch_records: usize,
    compression: ParquetCompression,
) -> Result<()> {
    let copybook_text = std::fs::read_to_string(copybook).context("Failed to read copybook file")?;
    let specs = parse_copybook(&copybook_text)?;
    let fixed_len: usize = specs.iter().map(|s| s.width()).sum();
    let record_len = if line_terminated { fixed_len + 1 } else { fixed_len };

    let in_file = File::open(input).context("Failed to open input file")?;
    // SAFETY: read-only memory map over a valid file descriptor.
    let mmap = unsafe { MmapOptions::new().map(&in_file).context("Failed to mmap input file")? };
    if mmap.len() % record_len != 0 {
        bail!(
            "Input size {} is not divisible by record length {}",
            mmap.len(),
            record_len
        );
    }
    let total_rows = mmap.len() / record_len;

    let out_file = File::create(output).context("Failed to create output parquet")?;
    let schema = schema_for_specs(&specs);
    let codec = match compression {
        ParquetCompression::Zstd => Compression::ZSTD(ZstdLevel::try_new(3)?),
        ParquetCompression::Snappy => Compression::SNAPPY,
        ParquetCompression::Uncompressed => Compression::UNCOMPRESSED,
    };
    let props = WriterProperties::builder().set_compression(codec).build();
    let writer =
        ArrowWriter::try_new(out_file, schema, Some(props)).context("Parquet init failed")?;

    // Pipeline: Rayon parses batches on all cores while a dedicated thread writes Parquet
    // (ZSTD) in strict row order. A serial parse→write loop leaves compression on one core;
    // overlapping parse with write uses the machine much more fully on large inputs.
    let batch_starts: Vec<usize> = (0..total_rows).step_by(batch_records).collect();
    let num_batches = batch_starts.len();
    if num_batches == 0 {
        writer.close()?;
        return Ok(());
    }

    let parse_threads = std::thread::available_parallelism()
        .map(|n| (n.get() as usize).max(2))
        .unwrap_or(4);
    let queue = (parse_threads * 4).max(16);

    let specs = Arc::new(specs);
    let mmap = Arc::new(mmap);

    type Msg = Result<(usize, RecordBatch), String>;
    let (tx, rx) = sync_channel::<Msg>(queue);

    let mut writer = writer;
    let writer_handle = thread::spawn(move || -> Result<()> {
        let mut next_expected = 0usize;
        let mut pending: BTreeMap<usize, RecordBatch> = BTreeMap::new();
        while next_expected < num_batches {
            match rx.recv() {
                Ok(Ok((idx, batch))) => {
                    pending.insert(idx, batch);
                    while let Some(b) = pending.remove(&next_expected) {
                        writer.write(&b).context("parquet write")?;
                        next_expected += 1;
                    }
                }
                Ok(Err(e)) => bail!("batch parse failed: {e}"),
                Err(_) => bail!(
                    "writer channel closed early ({}/{} batches)",
                    next_expected,
                    num_batches
                ),
            }
        }
        writer.close().context("parquet close")?;
        Ok(())
    });

    let pool = rayon::ThreadPoolBuilder::new()
        .num_threads(parse_threads)
        .build()
        .context("rayon ThreadPoolBuilder")?;

    let tx_clone = tx.clone();
    let parse_result: Result<()> = pool.install(|| {
        batch_starts
            .par_iter()
            .enumerate()
            .try_for_each(|(batch_idx, &start_row)| {
                let end_row = std::cmp::min(start_row + batch_records, total_rows);
                let start_byte = start_row * record_len;
                let end_byte = end_row * record_len;
                let rows_slice = &mmap[start_byte..end_byte];
                match parse_batch(&specs, rows_slice, record_len, end_row - start_row) {
                    Ok(batch) => tx_clone
                        .send(Ok((batch_idx, batch)))
                        .map_err(|e| anyhow::anyhow!("send batch {batch_idx}: {e}")),
                    Err(e) => tx_clone
                        .send(Err(e.to_string()))
                        .map_err(|e| anyhow::anyhow!("send error for batch {batch_idx}: {e}")),
                }
            })
    });

    drop(tx);
    let join_result = writer_handle
        .join()
        .map_err(|_| anyhow::anyhow!("writer thread panicked"))?;
    parse_result?;
    join_result?;
    Ok(())
}

#[pyfunction(signature=(input, copybook, output, line_terminated=true, batch_records=500_000, compression="zstd"))]
fn parse_copy_to_parquet(
    input: &str,
    copybook: &str,
    output: &str,
    line_terminated: bool,
    batch_records: usize,
    compression: &str,
) -> PyResult<()> {
    let compression = ParquetCompression::from_str(compression)
        .map_err(|e| PyRuntimeError::new_err(e.to_string()))?;
    convert_fixed_to_parquet(
        Path::new(input),
        Path::new(copybook),
        Path::new(output),
        line_terminated,
        batch_records,
        compression,
    )
    .map_err(|e| PyRuntimeError::new_err(e.to_string()))
}

#[pymodule]
fn fixed2parquet(_py: Python<'_>, m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(parse_copy_to_parquet, m)?)?;
    Ok(())
}

