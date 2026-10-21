use anyhow::{bail, Context, Result};
use std::ffi::{OsStr, OsString};
#[cfg(windows)]
use std::os::windows::process::CommandExt;
use std::path::Path;
use std::process::{Command, Output};

#[cfg(windows)]
const CREATE_NO_WINDOW: u32 = 0x08000000;

fn ghostscript_command(program: impl AsRef<OsStr>) -> Command {
    let command = Command::new(program);
    #[cfg(windows)]
    let command = {
        let mut command = command;
        command.creation_flags(CREATE_NO_WINDOW);
        command
    };
    command
}

#[derive(Debug, Default, Clone, Copy, PartialEq, Eq)]
pub enum CompressionProfile {
    #[default]
    Ebook,
}

impl CompressionProfile {
    pub fn name(self) -> &'static str {
        match self {
            Self::Ebook => "/ebook",
        }
    }
}

#[cfg(any(target_os = "macos", test))]
fn macos_ghostscript_program(path: Option<&OsStr>, known_locations: &[&Path]) -> OsString {
    if path.is_some_and(|value| {
        std::env::split_paths(value).any(|directory| directory.join("gs").is_file())
    }) {
        return OsString::from("gs");
    }
    known_locations
        .iter()
        .find(|location| location.is_file())
        .map(|location| location.as_os_str().to_os_string())
        .unwrap_or_else(|| OsString::from("gs"))
}

pub fn executable() -> OsString {
    #[cfg(target_os = "macos")]
    {
        return macos_ghostscript_program(
            std::env::var_os("PATH").as_deref(),
            &[
                Path::new("/opt/homebrew/bin/gs"),
                Path::new("/usr/local/bin/gs"),
            ],
        );
    }
    #[cfg(not(target_os = "macos"))]
    {
        if cfg!(windows) {
            OsString::from("gswin64c")
        } else {
            OsString::from("gs")
        }
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
    let program = executable();
    let output = ghostscript_command(&program).arg("--version").output();
    match output {
        Ok(result) if result.status.success() => Ok(()),
        Ok(result) => bail!(
            "Ghostscript is unavailable (`{} --version` exited with {}). {}",
            program.to_string_lossy(),
            result.status,
            install_hint()
        ),
        Err(error) => bail!(
            "Ghostscript is unavailable (`{} --version`: {}). {}",
            program.to_string_lossy(),
            error,
            install_hint()
        ),
    }
}

pub fn build_args(input: &Path, output: &Path, profile: CompressionProfile) -> Vec<OsString> {
    let mut output_arg = OsString::from("-sOutputFile=");
    output_arg.push(output.as_os_str());
    vec![
        "-sDEVICE=pdfwrite".into(),
        "-dCompatibilityLevel=1.4".into(),
        format!("-dPDFSETTINGS={}", profile.name()).into(),
        "-dDetectDuplicateImages=true".into(),
        "-dNOPAUSE".into(),
        "-dQUIET".into(),
        "-dBATCH".into(),
        "-dPDFSTOPONERROR=true".into(),
        output_arg,
        input.as_os_str().to_os_string(),
    ]
}

pub fn diagnostics(output: &Output) -> String {
    format!(
        "stdout:\n{}\nstderr:\n{}",
        String::from_utf8_lossy(&output.stdout).trim(),
        String::from_utf8_lossy(&output.stderr).trim(),
    )
}

fn has_fatal_diagnostic(bytes: &[u8]) -> bool {
    String::from_utf8_lossy(bytes).lines().any(|line| {
        // Ghostscript decorates some PDF errors with leading asterisks.
        // Do not reject arbitrary mentions of "error" inside warnings.
        let line = line
            .trim_start()
            .trim_start_matches('*')
            .trim_start()
            .to_ascii_lowercase();
        line.starts_with("error:")
            || line.starts_with("error ")
            || line.starts_with("fatal error")
            || line.starts_with("unrecoverable error")
            || (line.starts_with("gpl ghostscript") && line.contains(": unrecoverable error"))
            || line.starts_with("no pages will be processed")
            || line.starts_with("this file had errors")
            || line.starts_with("this file requires a password")
    })
}

pub fn run(input: &Path, output: &Path, profile: CompressionProfile) -> Result<Output> {
    let result = ghostscript_command(executable())
        .args(build_args(input, output, profile))
        .output()
        .with_context(|| format!("Could not start Ghostscript. {}", install_hint()))?;
    if !result.status.success()
        || has_fatal_diagnostic(&result.stdout)
        || has_fatal_diagnostic(&result.stderr)
    {
        bail!(
            "Ghostscript failed using {} ({}). {}",
            profile.name(),
            result.status,
            diagnostics(&result)
        );
    }
    // Retain both streams so candidate-validation failures include the
    // conversion's diagnostics even when the subprocess exited successfully.
    Ok(result)
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::ffi::OsString;
    use std::path::Path;

    #[test]
    fn macos_ghostscript_finds_homebrew_without_a_shell_path() {
        let directory = tempfile::tempdir().unwrap();
        let homebrew = directory.path().join("homebrew");
        std::fs::create_dir(&homebrew).unwrap();
        let executable = homebrew.join("gs");
        std::fs::write(&executable, b"test").unwrap();

        assert_eq!(
            macos_ghostscript_program(Some(OsStr::new("")), &[executable.as_path()]),
            executable.as_os_str()
        );
        assert_eq!(
            macos_ghostscript_program(Some(homebrew.as_os_str()), &[executable.as_path()]),
            OsStr::new("gs")
        );
    }

    #[cfg(windows)]
    #[test]
    fn subprocess_has_no_console_and_preserves_diagnostics() {
        const PROBE: &str = "PDF_SQUEEZE_CONSOLE_PROBE";
        if std::env::var_os(PROBE).is_some() {
            #[link(name = "kernel32")]
            extern "system" {
                fn GetConsoleWindow() -> *mut std::ffi::c_void;
            }

            // SAFETY: This API takes no arguments and returns a borrowed handle.
            assert!(unsafe { GetConsoleWindow() }.is_null());
            println!("console probe stdout");
            eprintln!("console probe stderr");
            return;
        }

        // The debug test executable is a console program, like gswin64c.exe.
        let result = ghostscript_command(std::env::current_exe().unwrap())
            .args([
                "--exact",
                "gs::tests::subprocess_has_no_console_and_preserves_diagnostics",
                "--nocapture",
            ])
            .env(PROBE, "1")
            .output()
            .unwrap();
        assert!(result.status.success(), "{result:?}");
        assert!(String::from_utf8_lossy(&result.stdout).contains("console probe stdout"));
        assert!(String::from_utf8_lossy(&result.stderr).contains("console probe stderr"));
    }

    #[test]
    fn builds_required_ghostscript_arguments() {
        let args = build_args(
            Path::new("input.pdf"),
            Path::new("result.pdf"),
            CompressionProfile::default(),
        );
        let expected: Vec<OsString> = [
            "-sDEVICE=pdfwrite",
            "-dCompatibilityLevel=1.4",
            "-dPDFSETTINGS=/ebook",
            "-dDetectDuplicateImages=true",
            "-dNOPAUSE",
            "-dQUIET",
            "-dBATCH",
            "-dPDFSTOPONERROR=true",
            "-sOutputFile=result.pdf",
            "input.pdf",
        ]
        .into_iter()
        .map(OsString::from)
        .collect();
        assert_eq!(args, expected);
    }
}
