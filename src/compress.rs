use crate::gs;
use anyhow::{anyhow, bail, Context, Result};
use std::fs;
use std::io::Read;
use std::path::Path;

pub const MIN_DPI: u32 = 50;
pub const MAX_DPI: u32 = 300;

pub fn format_mb(mb: f64) -> String {
    let precision = if mb < 0.01 { 6 } else { 2 };
    format!("{mb:.precision$} MB")
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct SearchResult {
    pub dpi: Option<u32>,
    pub size_bytes: u64,
    pub met_target: bool,
}

pub fn find_best_dpi(
    target_bytes: u64,
    original_size: u64,
    mut size_at_dpi: impl FnMut(u32) -> Result<u64>,
) -> Result<SearchResult> {
    if original_size <= target_bytes {
        return Ok(SearchResult {
            dpi: None,
            size_bytes: original_size,
            met_target: true,
        });
    }
    let min_size = size_at_dpi(MIN_DPI)?;
    let mut best = SearchResult {
        dpi: Some(MIN_DPI),
        size_bytes: min_size,
        met_target: min_size <= target_bytes,
    };
    if !best.met_target {
        return Ok(best);
    }

    let max_size = size_at_dpi(MAX_DPI)?;
    if max_size <= target_bytes {
        return Ok(SearchResult {
            dpi: Some(MAX_DPI),
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
                dpi: Some(dpi),
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
    let mut file = fs::File::open(input).with_context(|| {
        format!(
            "Could not open input PDF '{}': check permissions",
            input.display()
        )
    })?;
    let mut header = [0_u8; 5];
    file.read_exact(&mut header).with_context(|| {
        format!(
            "Input '{}' is not a PDF file (missing PDF header)",
            input.display()
        )
    })?;
    if &header != b"%PDF-" {
        bail!(
            "Input '{}' is not a PDF file (missing PDF header)",
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
    let original_size = fs::metadata(&input)
        .with_context(|| {
            format!(
                "Could not read input size '{}': check the file",
                input.display()
            )
        })?
        .len();
    if output == input || fs::canonicalize(output).is_ok_and(|path| path == input) {
        bail!("Output path must differ from the input PDF");
    }
    if fs::symlink_metadata(output).is_ok() {
        bail!(
            "Output '{}' already exists. Choose a different output path",
            output.display()
        );
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

    let mut attempts = Vec::<(u32, tempfile::TempPath)>::new();
    let result = find_best_dpi(target_bytes, original_size, |dpi| {
        let trial = tempfile::Builder::new()
            .suffix(".pdf")
            .tempfile_in(trials.path())
            .context("Could not create a temporary PDF")?
            .into_temp_path();
        gs::run(&input, &trial, dpi)?;
        let size = fs::metadata(&trial)
            .with_context(|| {
                format!(
                    "Ghostscript did not create '{}': check the input PDF",
                    trial.display()
                )
            })?
            .len();
        attempts.push((dpi, trial));
        Ok(size)
    })?;
    let winner = if let Some(dpi) = result.dpi {
        let winner_index = attempts
            .iter()
            .position(|(attempt_dpi, _)| *attempt_dpi == dpi)
            .ok_or_else(|| anyhow!("Selected PDF was not found"))?;
        attempts.swap_remove(winner_index).1
    } else {
        let original = tempfile::Builder::new()
            .suffix(".pdf")
            .tempfile_in(trials.path())
            .context("Could not create a temporary PDF")?
            .into_temp_path();
        let copied = fs::copy(&input, &original).with_context(|| {
            format!(
                "Could not copy input PDF '{}': check the file",
                input.display()
            )
        })?;
        if copied != original_size {
            bail!("Input PDF changed during compression. Please try again");
        }
        original
    };
    winner.persist_noclobber(output).with_context(|| {
        format!(
            "Could not save '{}': it may already exist, or the output folder may not be writable",
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
        let result = find_best_dpi(100, 300, |dpi| {
            tried.push(dpi);
            Ok(200)
        })
        .unwrap();
        assert_eq!(tried, [50]);
        assert_eq!(result.dpi, Some(50));
        assert_eq!(result.size_bytes, 200);
        assert!(!result.met_target);
    }

    #[test]
    fn chooses_300_when_it_fits() {
        let result = find_best_dpi(300, 400, |dpi| Ok(u64::from(dpi))).unwrap();
        assert_eq!(result.dpi, Some(300));
        assert!(result.met_target);
    }

    #[test]
    fn finds_largest_fitting_dpi_within_five_dpi() {
        let result = find_best_dpi(200, 400, |dpi| Ok(u64::from(dpi))).unwrap();
        assert!((195..=200).contains(&result.dpi.unwrap()));
        assert_eq!(result.size_bytes, u64::from(result.dpi.unwrap()));
        assert!(result.met_target);
    }

    #[test]
    fn propagates_sizing_errors() {
        let result = find_best_dpi(100, 300, |_| anyhow::bail!("sizing failed"));
        assert!(result.unwrap_err().to_string().contains("sizing failed"));
    }

    #[test]
    fn preserves_original_when_it_already_fits() {
        let mut tried = false;
        let result = find_best_dpi(1_000, 346, |_| {
            tried = true;
            Ok(2_398)
        })
        .unwrap();
        assert!(!tried);
        assert_eq!(result.dpi, None);
        assert_eq!(result.size_bytes, 346);
        assert!(result.met_target);
    }

    #[test]
    fn displays_small_megabyte_values_without_rounding_to_zero() {
        assert_eq!(format_mb(0.000001), "0.000001 MB");
        assert_eq!(format_mb(12.345), "12.35 MB");
    }

    #[test]
    fn rejects_non_pdf_content_before_ghostscript() {
        let directory = tempfile::tempdir().unwrap();
        let input = directory.path().join("fake.pdf");
        std::fs::write(&input, b"not a PDF").unwrap();
        let error = validate_input(&input).unwrap_err().to_string();
        assert!(error.contains("not a PDF"), "{error}");
    }

    #[test]
    fn accepts_pdf_header() {
        let input = Path::new(concat!(
            env!("CARGO_MANIFEST_DIR"),
            "/tests/fixtures/tiny.pdf"
        ));
        validate_input(input).unwrap();
    }

    #[test]
    fn never_replaces_an_existing_output() {
        let directory = tempfile::tempdir().unwrap();
        let output = directory.path().join("existing.pdf");
        std::fs::write(&output, b"keep this").unwrap();
        let input = Path::new(concat!(
            env!("CARGO_MANIFEST_DIR"),
            "/tests/fixtures/tiny.pdf"
        ));
        let error = compress_pdf(input, &output, 1.0).unwrap_err().to_string();
        assert!(error.contains("already exists"), "{error}");
        assert_eq!(std::fs::read(output).unwrap(), b"keep this");
    }
}
