use crate::gs;
use anyhow::{anyhow, bail, Context, Result};
use std::fs;
use std::io::{Read, Seek, SeekFrom};
use std::path::Path;

pub const MIN_DPI: u32 = 72;
pub const MAX_DPI: u32 = 300;
pub const ESTIMATED_TOTAL_STEPS: usize = 8;

#[derive(Debug, Clone, Copy)]
pub struct ProgressUpdate {
    pub current_step: usize,
    pub total_steps: usize,
}

pub fn format_mb(mb: f64) -> String {
    let precision = if mb < 0.01 { 6 } else { 2 };
    format!("{mb:.precision$} MB")
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct SearchResult {
    pub dpi: Option<u32>,
    pub size_bytes: u64,
    pub original_size_bytes: u64,
}

pub fn find_best_dpi(
    original_size: u64,
    mut size_at_dpi: impl FnMut(u32) -> Result<u64>,
) -> Result<SearchResult> {
    let min_size = size_at_dpi(MIN_DPI)?;
    let max_size = size_at_dpi(MAX_DPI)?;
    let (mut best_dpi, mut best_size) = if max_size < min_size {
        (MAX_DPI, max_size)
    } else {
        (MIN_DPI, min_size)
    };

    let mut lo = MIN_DPI;
    let mut lo_size = min_size;
    let mut hi = MAX_DPI;
    while hi - lo > 5 {
        let dpi = lo + (hi - lo) / 2;
        let size = size_at_dpi(dpi)?;
        if size < best_size {
            best_dpi = dpi;
            best_size = size;
        }
        if size < lo_size {
            lo = dpi;
            lo_size = size;
        } else {
            hi = dpi;
        }
    }
    if best_size < original_size {
        Ok(SearchResult {
            dpi: Some(best_dpi),
            size_bytes: best_size,
            original_size_bytes: original_size,
        })
    } else {
        Ok(SearchResult {
            dpi: None,
            size_bytes: original_size,
            original_size_bytes: original_size,
        })
    }
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

fn validate_candidate(path: &Path) -> Result<u64> {
    let mut file = fs::File::open(path).context("Could not open the candidate PDF")?;
    let metadata = file
        .metadata()
        .context("Could not inspect the candidate PDF")?;
    if !metadata.is_file() || metadata.len() == 0 {
        bail!("Candidate PDF is empty or is not a regular file");
    }

    let mut header = [0_u8; 8];
    file.read_exact(&mut header)
        .context("Candidate PDF has a missing or truncated header")?;
    if &header[..5] != b"%PDF-"
        || !header[5].is_ascii_digit()
        || header[6] != b'.'
        || !header[7].is_ascii_digit()
    {
        bail!("Candidate PDF has an invalid header");
    }

    // Cheap checks for missing/truncated output, not a full PDF parser.
    // Ghostscript's strict error mode and diagnostics guard input corruption;
    // these checks guard the candidate before it can win on file size.
    let tail_len = metadata.len().min(1024) as usize;
    file.seek(SeekFrom::End(-(tail_len as i64)))?;
    let mut tail = vec![0; tail_len];
    file.read_exact(&mut tail)?;
    let tail = tail.trim_ascii_end();
    let trailer = tail
        .strip_suffix(b"%%EOF")
        .context("Candidate PDF is missing its EOF marker")?;
    let marker = trailer
        .windows(b"startxref".len())
        .rposition(|bytes| bytes == b"startxref")
        .context("Candidate PDF is missing its cross-reference trailer")?;
    let offset = std::str::from_utf8(&trailer[marker + b"startxref".len()..])?
        .trim()
        .parse::<u64>()
        .context("Candidate PDF has an invalid cross-reference offset")?;
    if offset < header.len() as u64 || offset >= metadata.len() {
        bail!("Candidate PDF cross-reference offset is outside the file");
    }
    // Conversion explicitly requests PDF 1.4, which uses a cross-reference
    // table rather than a PDF 1.5 cross-reference stream.
    file.seek(SeekFrom::Start(offset))?;
    let mut xref = [0_u8; 5];
    file.read_exact(&mut xref)
        .context("Candidate PDF has a truncated cross-reference table")?;
    if &xref[..4] != b"xref" || !xref[4].is_ascii_whitespace() {
        bail!("Candidate PDF cross-reference offset does not point to a table");
    }
    Ok(metadata.len())
}

pub fn compress_pdf(
    input: &Path,
    output: &Path,
    mut on_progress: impl FnMut(ProgressUpdate),
) -> Result<SearchResult> {
    validate_input(input)?;
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
    let mut current_step = 0;
    let result = find_best_dpi(original_size, |dpi| {
        let trial = tempfile::Builder::new()
            .suffix(".pdf")
            .tempfile_in(trials.path())
            .context("Could not create a temporary PDF")?
            .into_temp_path();
        let invocation = gs::run(&input, &trial, dpi);
        current_step += 1;
        on_progress(ProgressUpdate {
            current_step,
            total_steps: ESTIMATED_TOTAL_STEPS,
        });
        let invocation = invocation?;
        let size = validate_candidate(&trial).with_context(|| {
            format!(
                "Ghostscript produced invalid PDF output at {dpi} DPI. {}",
                gs::diagnostics(&invocation)
            )
        })?;
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
    fn keeps_smallest_output_seen_during_search() {
        let mut tried = Vec::new();
        let result = find_best_dpi(10_000, |dpi| {
            let size = if dpi == 186 {
                800
            } else {
                1_000 + u64::from(dpi)
            };
            tried.push((dpi, size));
            Ok(size)
        })
        .unwrap();
        assert_eq!(result.dpi, Some(186));
        assert_eq!(result.size_bytes, 800);
        assert_eq!(
            result.size_bytes,
            tried.iter().map(|(_, size)| *size).min().unwrap()
        );
    }

    #[test]
    fn considers_300_dpi_when_it_is_smallest() {
        let result = find_best_dpi(10_000, |dpi| Ok(5_000 - u64::from(dpi))).unwrap();
        assert_eq!(result.dpi, Some(300));
        assert_eq!(result.size_bytes, 4_700);
    }

    #[test]
    fn never_samples_below_72_dpi() {
        let mut tried = Vec::new();
        let result = find_best_dpi(10_000, |dpi| {
            tried.push(dpi);
            Ok(u64::from(dpi))
        })
        .unwrap();
        assert!(tried.contains(&72));
        assert!(tried.iter().all(|dpi| (72..=300).contains(dpi)));
        assert!(tried.len() <= 8);
        assert_eq!(result.dpi, Some(72));
    }

    #[test]
    fn propagates_sizing_errors() {
        let result = find_best_dpi(300, |_| anyhow::bail!("sizing failed"));
        assert!(result.unwrap_err().to_string().contains("sizing failed"));
    }

    #[test]
    fn keeps_original_when_every_compressed_result_is_larger() {
        let mut tried = Vec::new();
        let result = find_best_dpi(346, |dpi| {
            tried.push(dpi);
            Ok(2_398)
        })
        .unwrap();
        assert!(!tried.is_empty());
        assert_eq!(result.dpi, None);
        assert_eq!(result.size_bytes, 346);
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
        let error = compress_pdf(input, &output, |_| {})
            .unwrap_err()
            .to_string();
        assert!(error.contains("already exists"), "{error}");
        assert_eq!(std::fs::read(output).unwrap(), b"keep this");
    }
}
