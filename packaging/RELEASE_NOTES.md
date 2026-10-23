# PDF Squeeze v0.1.0

PDF Squeeze's first release provides a desktop app and command-line tool for compressing one PDF at a time. It runs one Ghostscript `/ebook` conversion, validates the result, and saves it only when it is smaller. Otherwise, it saves an unchanged copy of the input. Existing output files are protected.

## Downloads

- Windows x64: `pdf-squeeze-windows-x64.zip`
- Linux x64 (built on Ubuntu 22.04): `pdf-squeeze-linux-x64.tar.gz`
- macOS Apple Silicon: `pdf-squeeze-macos-arm64.zip`
- macOS Intel: `pdf-squeeze-macos-x64.zip`

Use `SHA256SUMS.txt` from this release to check downloaded archives. Each archive contains an `INSTALL.md`, the project's `LICENSE`, `THIRD_PARTY_NOTICES.md`, `LICENSING.md`, and the supporting third-party notices. Ghostscript is a separate required installation; see the [official Ghostscript downloads](https://ghostscript.com/releases/gsdnld.html). It is not included in these packages.

Open the app with no arguments for the GUI. For CLI use, run `pdf-squeeze input.pdf --output result.pdf` (or `pdf-squeeze.exe` on Windows). Without `--output`, the app writes `<input_stem>_squeezed.pdf` beside the input.

In one real-world Windows test, an 80 MB PDF became 17 MB. This is one example, not a promised result for other files. The `/ebook` profile can change image quality and other PDF properties; inspect your output.

The Linux binary is built on Ubuntu 22.04; compatibility with other distributions is not guaranteed. The macOS app bundles are not Developer ID signed or notarized, so Gatekeeper may block them. See each archive's `INSTALL.md` before use. Ghostscript's separate licensing terms should be reviewed for the intended use.

## Highlights

- Desktop file picker, progress state, and file-size savings summary.
- CLI mode with the same single-pass compression engine.
- Native packages for Windows x64, Linux x64, macOS Apple Silicon, and macOS Intel.
- Platform application icons and bundled third-party licensing documentation.
