use std::process::Command;

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
