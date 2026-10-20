use std::process::Command;

#[test]
#[ignore = "requires Ghostscript installed"]
fn compresses_fixture_with_real_ghostscript() {
    let directory = tempfile::tempdir().expect("create test directory");
    let preserved = directory.path().join("preserved.pdf");
    let output = directory.path().join("squeezed.pdf");
    let input = concat!(env!("CARGO_MANIFEST_DIR"), "/tests/fixtures/tiny.pdf");

    let first = Command::new(env!("CARGO_BIN_EXE_pdf-squeeze"))
        .arg(input)
        .arg("--target-mb")
        .arg("1")
        .arg("--output")
        .arg(&preserved)
        .output()
        .expect("start pdf-squeeze");
    assert!(
        first.status.success(),
        "{}",
        String::from_utf8_lossy(&first.stderr)
    );
    assert_eq!(
        std::fs::read(input).expect("read fixture"),
        std::fs::read(preserved).expect("read preserved output")
    );

    let result = Command::new(env!("CARGO_BIN_EXE_pdf-squeeze"))
        .arg(input)
        .arg("--target-mb")
        .arg("0.0001")
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
    assert!(std::fs::metadata(output).expect("read output size").len() > 100);
    assert!(String::from_utf8_lossy(&result.stderr).contains("Warning"));
}
