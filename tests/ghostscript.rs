use std::process::Command;

fn run_app(input: &std::path::Path, output: &std::path::Path) -> std::process::Output {
    Command::new(env!("CARGO_BIN_EXE_pdf-squeeze"))
        .arg(input)
        .arg("--output")
        .arg(output)
        .output()
        .expect("start pdf-squeeze")
}

fn assert_failed_without_output(
    result: &std::process::Output,
    input: &std::path::Path,
    original: &[u8],
    output: &std::path::Path,
) {
    assert!(!result.status.success(), "unexpected success: {result:?}");
    assert!(!output.exists(), "failed conversion published an output");
    assert_eq!(std::fs::read(input).unwrap(), original);
    let stdout = String::from_utf8_lossy(&result.stdout);
    assert!(!stdout.contains("Compressed from"), "{stdout}");
    assert!(!stdout.contains("Original kept"), "{stdout}");
}

#[test]
#[ignore = "requires Ghostscript installed"]
fn keeps_fixture_when_ghostscript_cannot_shrink_it() {
    let directory = tempfile::tempdir().expect("create test directory");
    let output = directory.path().join("squeezed.pdf");
    let input = concat!(env!("CARGO_MANIFEST_DIR"), "/tests/fixtures/tiny.pdf");

    let result = Command::new(env!("CARGO_BIN_EXE_pdf-squeeze"))
        .arg(input)
        .arg("--output")
        .arg(&output)
        .output()
        .expect("start pdf-squeeze");

    assert!(
        result.status.success(),
        "{}",
        String::from_utf8_lossy(&result.stderr)
    );
    assert!(output.is_file());
    assert_eq!(
        std::fs::read(input).expect("read fixture"),
        std::fs::read(output).expect("read output")
    );
    assert!(String::from_utf8_lossy(&result.stdout).contains("Original kept"));
}

#[test]
#[ignore = "requires Ghostscript installed"]
fn rejects_corrupt_pdf_without_publishing_or_leaving_trials() {
    let directory = tempfile::tempdir().unwrap();
    let input = directory.path().join("corrupt.pdf");
    let output = directory.path().join("squeezed.pdf");
    let mut original = b"%PDF-1.4\nnot a PDF document\n".to_vec();
    original.extend_from_slice(&[b' '; 8192]);
    original.extend_from_slice(b"\n%%EOF\n");
    std::fs::write(&input, &original).unwrap();

    let result = run_app(&input, &output);

    assert_failed_without_output(&result, &input, &original, &output);
    assert!(String::from_utf8_lossy(&result.stderr).contains("Ghostscript"));
    assert_eq!(std::fs::read_dir(directory.path()).unwrap().count(), 1);
}

#[test]
#[ignore = "requires Ghostscript installed"]
fn explains_password_protected_input_without_publishing_output() {
    let directory = tempfile::tempdir().unwrap();
    let input = directory.path().join("encrypted.pdf");
    let output = directory.path().join("squeezed.pdf");
    let fixture = concat!(env!("CARGO_MANIFEST_DIR"), "/tests/fixtures/tiny.pdf");
    let mut output_arg = std::ffi::OsString::from("-sOutputFile=");
    output_arg.push(&input);
    let encrypted = Command::new(if cfg!(windows) { "gswin64c" } else { "gs" })
        .args(["-sDEVICE=pdfwrite", "-dBATCH", "-dNOPAUSE", "-dQUIET"])
        .args(["-sUserPassword=test-password", "-sOwnerPassword=test-owner"])
        .arg(output_arg)
        .arg(fixture)
        .output()
        .expect("generate encrypted fixture");
    assert!(encrypted.status.success(), "{encrypted:?}");
    let original = std::fs::read(&input).unwrap();

    let result = run_app(&input, &output);

    assert_failed_without_output(&result, &input, &original, &output);
    let error = String::from_utf8_lossy(&result.stderr).to_ascii_lowercase();
    assert!(error.contains("password"), "{error}");
    assert_eq!(std::fs::read_dir(directory.path()).unwrap().count(), 1);
}

#[cfg(unix)]
mod simulated_ghostscript {
    use super::*;
    use std::os::unix::fs::PermissionsExt;

    // Isolate PATH on the application child so parallel tests cannot change
    // each other's Ghostscript. Only the external process is simulated.
    fn run_with_script(body: &str) -> (tempfile::TempDir, std::process::Output) {
        let directory = tempfile::tempdir().unwrap();
        let bin = directory.path().join("bin");
        std::fs::create_dir(&bin).unwrap();
        let script = bin.join("gs");
        let fixture = include_str!("fixtures/tiny.pdf");
        std::fs::write(
            &script,
            format!(
                "#!/bin/sh\nif [ \"$1\" = '--version' ]; then printf '10.0\\n'; exit 0; fi\n\
                 for arg in \"$@\"; do\n\
                 case \"$arg\" in -sOutputFile=*) output=${{arg#-sOutputFile=}} ;; esac\n\
                 done\n{body}\n"
            )
            .replace("VALID_PDF", fixture),
        )
        .unwrap();
        std::fs::set_permissions(&script, std::fs::Permissions::from_mode(0o700)).unwrap();
        let mut original = fixture.as_bytes().to_vec();
        original.extend_from_slice(&[b' '; 8192]);
        let input = directory.path().join("input.pdf");
        std::fs::write(&input, original).unwrap();
        let result = Command::new(env!("CARGO_BIN_EXE_pdf-squeeze"))
            .arg(&input)
            .arg("--output")
            .arg(directory.path().join("output.pdf"))
            .env("PATH", &bin)
            .output()
            .unwrap();
        (directory, result)
    }

    fn assert_rejected(body: &str, expected: &[&str]) {
        let (directory, result) = run_with_script(body);
        let input = directory.path().join("input.pdf");
        let mut original = include_bytes!("fixtures/tiny.pdf").to_vec();
        original.extend_from_slice(&[b' '; 8192]);
        assert_failed_without_output(
            &result,
            &input,
            &original,
            &directory.path().join("output.pdf"),
        );
        let error = String::from_utf8_lossy(&result.stderr);
        for message in expected {
            assert!(error.contains(message), "missing {message:?}: {error}");
        }
        assert_eq!(std::fs::read_dir(directory.path()).unwrap().count(), 2);
    }

    #[test]
    fn rejects_zero_exit_with_fatal_diagnostics_on_either_stream() {
        for message in [
            "   **** Error: corrupt PDF input",
            "GPL Ghostscript: Unrecoverable error, exit code 1",
            "   No pages will be processed (FirstPage > LastPage).",
            "   **** This file had errors that were repaired or ignored.",
        ] {
            for redirect in ["", " >&2"] {
                assert_rejected(
                    &format!(
                        "printf '%s' 'VALID_PDF' > \"$output\"\n\
                         printf '%s\\n' '{message}'{redirect}\nexit 0"
                    ),
                    &[message.trim()],
                );
            }
        }
    }

    #[test]
    fn retains_stdout_and_stderr_when_ghostscript_fails() {
        assert_rejected(
            "printf 'This file requires a password for access.\\n'\n\
             printf 'Unrecoverable error, exit code 1\\n' >&2\nexit 1",
            &["password", "Unrecoverable error"],
        );
    }

    #[test]
    fn rejects_missing_empty_and_malformed_candidates() {
        for body in [
            "printf '' > \"$output\"",
            "/bin/rm \"$output\"\nexit 0",
            "printf 'not a PDF' > \"$output\"",
            "printf '%%PDF-1.4\\ntruncated' > \"$output\"",
            "printf '%%PDF-1.4\\n%%%%EOF\\n' > \"$output\"",
            "printf '%%PDF-1.4\\nstartxref\\n999999\\n%%%%EOF\\n' > \"$output\"",
            "printf '%%PDF-1.4\\nstartxref\\n9\\n%%%%EOF\\n' > \"$output\"",
        ] {
            assert_rejected(body, &["invalid PDF output"]);
        }
    }

    #[test]
    fn allows_harmless_warnings_with_a_valid_candidate() {
        let (directory, result) = run_with_script(
            "printf 'Warning: substituted font; no fatal error.\\n' >&2\n\
             printf '%s' 'VALID_PDF' > \"$output\"",
        );
        assert!(result.status.success(), "{result:?}");
        assert_eq!(
            std::fs::read(directory.path().join("output.pdf")).unwrap(),
            include_bytes!("fixtures/tiny.pdf")
        );
        assert!(String::from_utf8_lossy(&result.stdout).contains("Compressed from"));
        assert_eq!(std::fs::read_dir(directory.path()).unwrap().count(), 3);
    }
}
