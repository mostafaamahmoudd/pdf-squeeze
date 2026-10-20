use crate::gs;
use anyhow::{bail, Context, Result};
use std::fs;
use std::path::Path;

pub const MIN_DPI: u32 = 50;
pub const MAX_DPI: u32 = 300;

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct SearchResult {
    pub dpi: u32,
    pub size_bytes: u64,
    pub met_target: bool,
}

pub fn find_best_dpi(
    target_bytes: u64,
    mut size_at_dpi: impl FnMut(u32) -> Result<u64>,
) -> Result<SearchResult> {
    let min_size = size_at_dpi(MIN_DPI)?;
    let mut best = SearchResult {
        dpi: MIN_DPI,
        size_bytes: min_size,
        met_target: min_size <= target_bytes,
    };
    if !best.met_target {
        return Ok(best);
    }

    let max_size = size_at_dpi(MAX_DPI)?;
    if max_size <= target_bytes {
        return Ok(SearchResult {
            dpi: MAX_DPI,
            size_bytes: max_size,
            met_target: true,
        });
    }

    let mut lo = MIN_DPI;
    let mut hi = MAX_DPI;
    while hi - lo > 5 {
        let dpi = lo + (hi - lo) / 2;
        let size = size_at_dpi(dpi)?;
        if size <= target_bytes {
            lo = dpi;
            best = SearchResult {
                dpi,
                size_bytes: size,
                met_target: true,
            };
        } else {
            hi = dpi;
        }
    }
    Ok(best)
}

pub fn validate_input(input: &Path) -> Result<()> {
    let metadata = fs::metadata(input).with_context(|| {
        format!(
            "Input PDF '{}' does not exist or cannot be read",
            input.display()
        )
    })?;
    if !metadata.is_file() {
        bail!("Input '{}' is not a file", input.display());
    }
    if !input
        .extension()
        .and_then(|extension| extension.to_str())
        .is_some_and(|extension| extension.eq_ignore_ascii_case("pdf"))
    {
        bail!(
            "Input '{}' is not a PDF file (.pdf required)",
            input.display()
        );
    }
    Ok(())
}

pub fn default_output_path(input: &Path) -> std::path::PathBuf {
    let mut name = input.file_stem().unwrap_or_default().to_os_string();
    name.push("_squeezed.pdf");
    input.with_file_name(name)
}

pub fn compress_pdf(input: &Path, output: &Path, target_mb: f64) -> Result<SearchResult> {
    validate_input(input)?;
    if !target_mb.is_finite() || target_mb <= 0.0 || target_mb > (u64::MAX as f64) / 1_000_000.0 {
        bail!("Target size must be a positive number of MB");
    }
    let target_bytes = (target_mb * 1_000_000.0).floor() as u64;
    if target_bytes == 0 {
        bail!("Target size must be at least one byte");
    }

    let input = fs::canonicalize(input).with_context(|| {
        format!(
            "Could not resolve input '{}': check the path",
            input.display()
        )
    })?;
    if output == input || fs::canonicalize(output).is_ok_and(|path| path == input) {
        bail!("Output path must differ from the input PDF");
    }
    let output_dir = output
        .parent()
        .filter(|parent| !parent.as_os_str().is_empty())
        .unwrap_or_else(|| Path::new("."));
    let trials = tempfile::tempdir_in(output_dir).with_context(|| {
        format!(
            "Could not create temporary files in '{}': check that the output folder exists and is writable",
            output_dir.display()
        )
    })?;
    gs::check_installed()?;

    let result = find_best_dpi(target_bytes, |dpi| {
        let trial = trials.path().join(format!("{dpi}.pdf"));
        gs::run(&input, &trial, dpi)?;
        fs::metadata(&trial)
            .map(|metadata| metadata.len())
            .with_context(|| {
                format!(
                    "Ghostscript did not create '{}': check the input PDF",
                    trial.display()
                )
            })
    })?;
    let winner = trials.path().join(format!("{}.pdf", result.dpi));
    fs::rename(&winner, output).with_context(|| {
        format!(
            "Could not save '{}': check that the output folder is writable",
            output.display()
        )
    })?;
    Ok(result)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn returns_minimum_attempt_when_target_is_unreachable() {
        let mut tried = Vec::new();
        let result = find_best_dpi(100, |dpi| {
            tried.push(dpi);
            Ok(200)
        })
        .unwrap();
        assert_eq!(tried, [50]);
        assert_eq!(result.dpi, 50);
        assert_eq!(result.size_bytes, 200);
        assert!(!result.met_target);
    }

    #[test]
    fn chooses_300_when_it_fits() {
        let result = find_best_dpi(300, |dpi| Ok(u64::from(dpi))).unwrap();
        assert_eq!(result.dpi, 300);
        assert!(result.met_target);
    }

    #[test]
    fn finds_largest_fitting_dpi_within_five_dpi() {
        let result = find_best_dpi(200, |dpi| Ok(u64::from(dpi))).unwrap();
        assert!((195..=200).contains(&result.dpi));
        assert_eq!(result.size_bytes, u64::from(result.dpi));
        assert!(result.met_target);
    }

    #[test]
    fn propagates_sizing_errors() {
        let result = find_best_dpi(100, |_| anyhow::bail!("sizing failed"));
        assert!(result.unwrap_err().to_string().contains("sizing failed"));
    }
}
