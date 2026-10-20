mod compress;
mod gs;
mod gui;

use anyhow::Result;
use clap::Parser;
use std::path::PathBuf;

#[derive(Parser)]
#[command(name = "pdf-squeeze", about = "Compress one PDF to a target size")]
struct Cli {
    #[arg(value_name = "INPUT")]
    input: PathBuf,
    #[arg(
        short = 't',
        long = "target-mb",
        default_value_t = 50.0,
        value_name = "MB"
    )]
    target_mb: f64,
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
    let result = compress::compress_pdf(&cli.input, &output, cli.target_mb, |_| {})?;
    let size = compress::format_mb(result.size_bytes as f64 / 1_000_000.0);
    match (result.dpi, result.met_target) {
        (None, _) => println!(
            "Already below target at {size}; no DPI change was needed. Saved unchanged to {}.",
            output.display()
        ),
        (Some(dpi), true) => println!(
            "Compressed to {size} at {dpi} DPI. Saved to {}.",
            output.display()
        ),
        (Some(_), false) => eprintln!(
            "Warning: the 50 DPI result is {size}, above the {} target. The smallest result was saved to {}.",
            compress::format_mb(cli.target_mb),
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
    fn defaults_target_to_fifty_mb() {
        let cli = Cli::try_parse_from(["pdf-squeeze", "input.pdf"]).unwrap();
        assert_eq!(cli.target_mb, 50.0);
        assert!(cli.output.is_none());
    }

    #[test]
    fn accepts_short_output_and_target_flags() {
        let cli = Cli::try_parse_from(["pdf-squeeze", "input.pdf", "-t", "12.5", "-o", "out.pdf"])
            .unwrap();
        assert_eq!(cli.target_mb, 12.5);
        assert_eq!(cli.output.unwrap(), std::path::PathBuf::from("out.pdf"));
    }
}
