use anyhow::{bail, Context, Result};
use std::ffi::OsString;
use std::path::Path;
use std::process::Command;

pub fn executable() -> &'static str {
    if cfg!(windows) {
        "gswin64c"
    } else {
        "gs"
    }
}

pub fn install_hint() -> &'static str {
    if cfg!(windows) {
        "On Windows, install Ghostscript with `choco install ghostscript`, then restart this app."
    } else if cfg!(target_os = "macos") {
        "On macOS, install Ghostscript with `brew install ghostscript`, then restart this app."
    } else {
        "On Linux, install Ghostscript with `sudo apt install ghostscript`, then restart this app."
    }
}

pub fn check_installed() -> Result<()> {
    let output = Command::new(executable()).arg("--version").output();
    match output {
        Ok(result) if result.status.success() => Ok(()),
        Ok(result) => bail!(
            "Ghostscript is unavailable (`{} --version` exited with {}). {}",
            executable(),
            result.status,
            install_hint()
        ),
        Err(error) => bail!(
            "Ghostscript is unavailable (`{} --version`: {}). {}",
            executable(),
            error,
            install_hint()
        ),
    }
}

pub fn build_args(input: &Path, output: &Path, dpi: u32) -> Vec<OsString> {
    let mut output_arg = OsString::from("-sOutputFile=");
    output_arg.push(output.as_os_str());
    vec![
        "-sDEVICE=pdfwrite".into(),
        "-dCompatibilityLevel=1.4".into(),
        "-dPDFSETTINGS=/ebook".into(),
        format!("-dColorImageResolution={dpi}").into(),
        format!("-dGrayImageResolution={dpi}").into(),
        format!("-dMonoImageResolution={dpi}").into(),
        "-dColorImageDownsampleThreshold=1.0".into(),
        "-dGrayImageDownsampleThreshold=1.0".into(),
        "-dMonoImageDownsampleThreshold=1.0".into(),
        "-dDetectDuplicateImages=true".into(),
        "-dNOPAUSE".into(),
        "-dQUIET".into(),
        "-dBATCH".into(),
        output_arg,
        input.as_os_str().to_os_string(),
    ]
}

pub fn run(input: &Path, output: &Path, dpi: u32) -> Result<()> {
    let result = Command::new(executable())
        .args(build_args(input, output, dpi))
        .output()
        .with_context(|| format!("Could not start Ghostscript. {}", install_hint()))?;
    if !result.status.success() {
        let stderr = String::from_utf8_lossy(&result.stderr);
        bail!(
            "Ghostscript failed at {dpi} DPI ({}): {}",
            result.status,
            stderr.trim()
        );
    }
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::ffi::OsString;
    use std::path::Path;

    #[test]
    fn builds_required_ghostscript_arguments() {
        let args = build_args(Path::new("input.pdf"), Path::new("result.pdf"), 125);
        let expected: Vec<OsString> = [
            "-sDEVICE=pdfwrite",
            "-dCompatibilityLevel=1.4",
            "-dPDFSETTINGS=/ebook",
            "-dColorImageResolution=125",
            "-dGrayImageResolution=125",
            "-dMonoImageResolution=125",
            "-dColorImageDownsampleThreshold=1.0",
            "-dGrayImageDownsampleThreshold=1.0",
            "-dMonoImageDownsampleThreshold=1.0",
            "-dDetectDuplicateImages=true",
            "-dNOPAUSE",
            "-dQUIET",
            "-dBATCH",
            "-sOutputFile=result.pdf",
            "input.pdf",
        ]
        .into_iter()
        .map(OsString::from)
        .collect();
        assert_eq!(args, expected);
    }
}
