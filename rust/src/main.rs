use std::path::PathBuf;

use anyhow::Result;
use clap::Parser;
use fixed2parquet::{convert_fixed_to_parquet, ParquetCompression};

#[derive(Parser, Debug)]
#[command(
    name = "fixed2parquet",
    version,
    about = "Read fixed-size ASCII records from COBOL copybook and write Parquet."
)]
struct Args {
    /// Input fixed-size ASCII file path.
    #[arg(long)]
    input: PathBuf,

    /// Copybook file path containing PIC definitions.
    #[arg(long)]
    copybook: PathBuf,

    /// Output Parquet file path.
    #[arg(long)]
    output: PathBuf,

    /// If set, records are line-terminated with '\n' in input.
    #[arg(long, default_value_t = true)]
    line_terminated: bool,

    /// Number of records per parquet batch write.
    #[arg(long, default_value_t = 500_000)]
    batch_records: usize,

    /// Parquet compression codec: zstd|snappy|uncompressed
    #[arg(long, default_value = "zstd")]
    compression: String,
}

fn main() -> Result<()> {
    let args = Args::parse();
    let compression = ParquetCompression::from_str(&args.compression)?;
    convert_fixed_to_parquet(
        &args.input,
        &args.copybook,
        &args.output,
        args.line_terminated,
        args.batch_records,
        compression,
    )
}

