mod compress;
mod gs;
mod gui;

use anyhow::Result;
use clap::Parser;
use std::path::PathBuf;

#[derive(Parser)]
#[command(name = "pdf-squeeze", about = "Compress one PDF to a smaller size")]
struct Cli {
    #[arg(value_name = "INPUT")]
    input: PathBuf,
    #[arg(short = 'o', long = "output", value_name = "PATH")]
    output: Option<PathBuf>,
}

fn main() {
    let result = if std::env::args_os().nth(1).is_none() {
        gui::run()
    } else {
        run_cli()
    };
    if let Err(error) = result {
        eprintln!("Error: {error:#}");
        std::process::exit(1);
    }
}

fn run_cli() -> Result<()> {
    let cli = Cli::parse();
    let output = cli
        .output
        .unwrap_or_else(|| compress::default_output_path(&cli.input));
    let result = compress::compress_pdf(&cli.input, &output, |_| {})?;
    match result.dpi {
        Some(dpi) => println!(
            "Compressed from {} to {} at {dpi} DPI. Saved to {}.",
            compress::format_mb(result.original_size_bytes as f64 / 1_000_000.0),
            compress::format_mb(result.size_bytes as f64 / 1_000_000.0),
            output.display()
        ),
        None => println!(
            "This file is already as small as it can get without quality loss. Original kept. Saved unchanged to {}.",
            output.display()
        ),
    }
    Ok(())
}

#[cfg(test)]
mod cli_tests {
    use super::*;
    use clap::Parser;

    #[test]
    fn accepts_input_without_a_target_flag() {
        let cli = Cli::try_parse_from(["pdf-squeeze", "input.pdf"]).unwrap();
        assert!(cli.output.is_none());
    }

    #[test]
    fn accepts_output_flag() {
        let cli = Cli::try_parse_from(["pdf-squeeze", "input.pdf", "-o", "out.pdf"]).unwrap();
        assert_eq!(cli.output.unwrap(), std::path::PathBuf::from("out.pdf"));
    }

    #[test]
    fn rejects_removed_target_flag() {
        assert!(Cli::try_parse_from(["pdf-squeeze", "input.pdf", "--target-mb", "5"]).is_err());
    }
}
