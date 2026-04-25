#![allow(unsafe_op_in_unsafe_fn)]

use pyo3::prelude::*;
use pyo3::exceptions::PyRuntimeError;
use pyo3::types::PyDict;
use std::fs::File;
use std::sync::Arc;
use std::path::Path;

use arrow::array::{ArrayRef, Float64Builder, Int64Builder, StringBuilder};
use arrow::datatypes::{Field, Schema, DataType};
use arrow::record_batch::RecordBatch;
use memmap2::Mmap;
use parquet::arrow::ArrowWriter;
use parquet::basic::Compression;
use parquet::file::properties::WriterProperties;
use rayon::prelude::*;

#[derive(Clone)]
enum ColType {
    String,
    Integer,
    Float,
}

impl ColType {
    fn from_str(raw: &str) -> Result<Self, String> {
        match raw.to_ascii_lowercase().as_str() {
            "string" | "str" | "text" | "utf8" => Ok(Self::String),
            "integer" | "int" | "int64" => Ok(Self::Integer),
            "float" | "double" | "float64" => Ok(Self::Float),
            other => Err(format!(
                "unsupported type '{other}', expected one of: string|integer|float"
            )),
        }
    }

    fn to_arrow_type(&self) -> DataType {
        match self {
            Self::String => DataType::Utf8,
            Self::Integer => DataType::Int64,
            Self::Float => DataType::Float64,
        }
    }
}

#[derive(Clone)]
struct ColDef {
    name: String,
    start: usize,
    len: usize,
    col_type: ColType,
}

enum ColBuilder {
    String(StringBuilder),
    Integer(Int64Builder),
    Float(Float64Builder),
}

impl ColBuilder {
    fn from_col_type(col_type: &ColType) -> Self {
        match col_type {
            ColType::String => Self::String(StringBuilder::new()),
            ColType::Integer => Self::Integer(Int64Builder::new()),
            ColType::Float => Self::Float(Float64Builder::new()),
        }
    }

    fn append_from_ascii(&mut self, value: &[u8], col_name: &str) -> Result<(), String> {
        let s = String::from_utf8_lossy(value);
        let trimmed = s.trim();
        match self {
            ColBuilder::String(builder) => {
                builder.append_value(trimmed);
                Ok(())
            }
            ColBuilder::Integer(builder) => {
                if trimmed.is_empty() {
                    builder.append_null();
                    return Ok(());
                }
                let parsed = trimmed.parse::<i64>().map_err(|e| {
                    format!("failed parsing integer column '{col_name}' value '{trimmed}': {e}")
                })?;
                builder.append_value(parsed);
                Ok(())
            }
            ColBuilder::Float(builder) => {
                if trimmed.is_empty() {
                    builder.append_null();
                    return Ok(());
                }
                let parsed = trimmed.parse::<f64>().map_err(|e| {
                    format!("failed parsing float column '{col_name}' value '{trimmed}': {e}")
                })?;
                builder.append_value(parsed);
                Ok(())
            }
        }
    }

    fn finish(self) -> ArrayRef {
        match self {
            ColBuilder::String(mut b) => Arc::new(b.finish()) as ArrayRef,
            ColBuilder::Integer(mut b) => Arc::new(b.finish()) as ArrayRef,
            ColBuilder::Float(mut b) => Arc::new(b.finish()) as ArrayRef,
        }
    }
}

#[pyfunction]
fn parse_and_write_parquet(
    input_path: String,
    output_folder: String,
    schema_dict: &Bound<'_, PyDict>,
    record_size: usize,
    rows_per_batch: usize, // Internal batching for memory management
) -> PyResult<()> {
    std::fs::create_dir_all(&output_folder).map_err(|e| PyRuntimeError::new_err(e.to_string()))?;
    // 1. Setup Schema
    let mut col_defs = Vec::new();
    let mut fields = Vec::new();
    for (name, pos) in schema_dict.iter() {
        let name_str: String = name.extract()?;
        let (start, len, col_type) = if let Ok(pos_typed) = pos.extract::<(usize, usize, String)>()
        {
            (
                pos_typed.0,
                pos_typed.1,
                ColType::from_str(&pos_typed.2).map_err(PyRuntimeError::new_err)?,
            )
        } else if let Ok(pos_untyped) = pos.extract::<(usize, usize)>() {
            (pos_untyped.0, pos_untyped.1, ColType::String)
        } else {
            return Err(PyRuntimeError::new_err(
                "schema values must be (start, len) or (start, len, type)",
            ));
        };
        col_defs.push(ColDef {
            name: name_str,
            start,
            len,
            col_type,
        });
    }
    for col in &col_defs {
        fields.push(Field::new(&col.name, col.col_type.to_arrow_type(), true));
    }
    let schema = Arc::new(Schema::new(fields));

    // 2. Map File
    let file = File::open(&input_path)?;
    let mmap = unsafe { Mmap::map(&file)? };
    let total_records = mmap.len() / record_size;
    
    // 3. Determine segmentation
    let num_cores = rayon::current_num_threads();
    let records_per_core = total_records / num_cores;

    // 4. Parallel execution: One task per core
    (0..num_cores)
        .into_par_iter()
        .try_for_each(|core_id| -> Result<(), String> {
        let start_rec = core_id * records_per_core;
        // Last core takes the remainder
        let end_rec = if core_id == num_cores - 1 { total_records } else { (core_id + 1) * records_per_core };
        
        let core_segment = &mmap[start_rec * record_size .. end_rec * record_size];
        
        // Prepare Parquet Writer for this specific core
        let shard_path = Path::new(&output_folder).join(format!("shard_{}.parquet", core_id));
        let shard_file = File::create(shard_path).map_err(|e| e.to_string())?;
        let props = WriterProperties::builder()
            .set_compression(Compression::SNAPPY)
            .build();
        let mut writer = ArrowWriter::try_new(shard_file, schema.clone(), Some(props))
            .map_err(|e| e.to_string())?;

        // Process in batches to avoid loading the entire segment into Arrow memory at once
        for batch_chunk in core_segment.chunks(record_size * rows_per_batch) {
            let mut builders = col_defs
                .iter()
                .map(|col| ColBuilder::from_col_type(&col.col_type))
                .collect::<Vec<_>>();
            
            for record in batch_chunk.chunks_exact(record_size) {
                for (i, col) in col_defs.iter().enumerate() {
                    let val = &record[col.start..(col.start + col.len)];
                    builders[i].append_from_ascii(val, &col.name)?;
                }
            }

            let arrays: Vec<ArrayRef> = builders.into_iter().map(ColBuilder::finish).collect();
            let batch = RecordBatch::try_new(schema.clone(), arrays).map_err(|e| e.to_string())?;
            writer.write(&batch).map_err(|e| e.to_string())?;
        }
        
        writer.close().map_err(|e| e.to_string())?;
        Ok(())
    })
    .map_err(PyRuntimeError::new_err)?;

    Ok(())
}

#[pymodule]
fn mainframe_tools(_py: Python<'_>, m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(parse_and_write_parquet, m)?)?;
    Ok(())
}