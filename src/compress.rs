use crate::gs;
use anyhow::{bail, Context, Result};
use std::fs;
use std::io::{Read, Seek, SeekFrom};
use std::path::Path;
use std::time::{Duration, Instant};

#[derive(Debug, Clone, Copy)]
pub enum CompressionStage {
    CheckingGhostscript,
    Compressing,
    ValidatingOutput,
    Saving,
}

impl CompressionStage {
    pub fn label(self) -> &'static str {
        match self {
            Self::CheckingGhostscript => "Checking Ghostscript…",
            Self::Compressing => "Compressing your PDF…",
            Self::ValidatingOutput => "Checking the compressed PDF…",
            Self::Saving => "Saving output…",
        }
    }
}

pub fn format_mb(mb: f64) -> String {
    let precision = if mb < 0.01 { 6 } else { 2 };
    format!("{mb:.precision$} MB")
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum CompressionOutcome {
    Compressed,
    Unchanged,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct CompressionResult {
    pub size_bytes: u64,
    pub original_size_bytes: u64,
    pub elapsed: Duration,
    pub compression_invocations: usize,
    pub profile: gs::CompressionProfile,
    pub outcome: CompressionOutcome,
}

impl CompressionResult {
    pub fn saved_percent(&self) -> f64 {
        if self.original_size_bytes == 0 {
            return 0.0;
        }
        self.original_size_bytes.saturating_sub(self.size_bytes) as f64
            / self.original_size_bytes as f64
            * 100.0
    }

    pub fn summary(&self) -> String {
        let outcome = match self.outcome {
            CompressionOutcome::Compressed => "Compressed from",
            CompressionOutcome::Unchanged => {
                "No smaller valid result with this profile. Original kept. Saved an unchanged copy:"
            }
        };
        format!(
            "{outcome} {} to {} ({:.1}% saved).\nProfile: {}; elapsed: {:.2} s; compression passes: {}.",
            format_mb(self.original_size_bytes as f64 / 1_000_000.0),
            format_mb(self.size_bytes as f64 / 1_000_000.0),
            self.saved_percent(),
            self.profile.name(),
            self.elapsed.as_secs_f64(),
            self.compression_invocations,
        )
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
    mut on_progress: impl FnMut(CompressionStage),
) -> Result<CompressionResult> {
    let started = Instant::now();
    let profile = gs::CompressionProfile::default();
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
    on_progress(CompressionStage::CheckingGhostscript);
    gs::check_installed()?;

    let trial = tempfile::Builder::new()
        .suffix(".pdf")
        .tempfile_in(trials.path())
        .context("Could not create a temporary PDF")?
        .into_temp_path();
    on_progress(CompressionStage::Compressing);
    let invocation = gs::run(&input, &trial, profile)?;
    on_progress(CompressionStage::ValidatingOutput);
    let candidate_size = validate_candidate(&trial).with_context(|| {
        format!(
            "Ghostscript produced invalid PDF output using {}. {}",
            profile.name(),
            gs::diagnostics(&invocation)
        )
    })?;

    on_progress(CompressionStage::Saving);
    let (size_bytes, outcome) = if candidate_size < original_size {
        (candidate_size, CompressionOutcome::Compressed)
    } else {
        // Reuse the private candidate path. Only the unchanged-copy outcome
        // needs a full-file copy; a smaller candidate is published directly.
        let copied = fs::copy(&input, &trial).with_context(|| {
            format!(
                "Could not copy input PDF '{}': check the file",
                input.display()
            )
        })?;
        if copied != original_size {
            bail!("Input PDF changed during compression. Please try again");
        }
        (original_size, CompressionOutcome::Unchanged)
    };
    trial.persist_noclobber(output).with_context(|| {
        format!(
            "Could not save '{}': it may already exist, or the output folder may not be writable",
            output.display()
        )
    })?;
    Ok(CompressionResult {
        size_bytes,
        original_size_bytes: original_size,
        elapsed: started.elapsed(),
        compression_invocations: 1,
        profile,
        outcome,
    })
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn reports_percentage_saved_from_the_published_sizes() {
        for (original_size_bytes, size_bytes, expected) in
            [(1_000, 250, 75.0), (1_000, 1_000, 0.0), (0, 0, 0.0)]
        {
            let result = CompressionResult {
                original_size_bytes,
                size_bytes,
                elapsed: Duration::ZERO,
                compression_invocations: 1,
                profile: gs::CompressionProfile::Ebook,
                outcome: CompressionOutcome::Compressed,
            };
            assert_eq!(result.saved_percent(), expected);
        }
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
