use std::process::Command;

#[test]
#[ignore = "requires Ghostscript installed"]
fn compresses_fixture_with_real_ghostscript() {
    let directory = tempfile::tempdir().expect("create test directory");
    let output = directory.path().join("squeezed.pdf");
    let input = concat!(env!("CARGO_MANIFEST_DIR"), "/tests/fixtures/tiny.pdf");

    let result = Command::new(env!("CARGO_BIN_EXE_pdf-squeeze"))
        .arg(input)
        .arg("--target-mb")
        .arg("1")
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
    assert!(std::fs::metadata(output).expect("read output size").len() <= 1_000_000);
}
