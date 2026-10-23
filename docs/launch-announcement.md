# PDF Squeeze v0.1.0 launch announcement — draft

PDF Squeeze is a small desktop app and CLI for compressing one PDF at a time.
Pick a PDF and an output path, then it runs one Ghostscript `/ebook` pass,
validates the result, and reports the size saved. If the conversion is not
smaller, it saves an unchanged copy of the original. Existing output files
are protected.

The first release is planned for Windows x64, Linux x64, macOS Apple Silicon,
and macOS Intel. Ghostscript is installed separately. In one real-world
Windows test, an 80 MB PDF became 17 MB; results vary by document, and the
`/ebook` profile can change image quality.

When the release is approved, download the matching archive and
`SHA256SUMS.txt` from [GitHub Releases](https://github.com/mostafaamahmoudd/rust-pdf-compressor/releases).
Installation steps and source code are in the [repository](https://github.com/mostafaamahmoudd/rust-pdf-compressor).

**Hold publication:** This announcement is a draft until the decisions in
[release readiness](release-readiness.md) are closed and the Release exists.
