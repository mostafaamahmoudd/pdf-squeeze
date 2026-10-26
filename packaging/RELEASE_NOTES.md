# PDF Squeeze v0.1.0

This first public, experimental release provides a desktop app and command-line tool for local PDF compression powered by Ghostscript. PDF Squeeze does not upload documents to an online service. It runs one Ghostscript `/ebook` conversion, validates the result, and saves it only when it is smaller. Otherwise, it saves an unchanged copy of the input. The original input is never modified, and the app refuses to replace an existing output file.

## Downloads

- Windows x64: `pdf-squeeze-windows-x64.zip` — [installation instructions](https://github.com/mostafaamahmoudd/pdf-squeeze/blob/master/packaging/INSTALL-WINDOWS.md).
- Linux x64 (built on Ubuntu 22.04): `pdf-squeeze-linux-x64.tar.gz` — [installation instructions](https://github.com/mostafaamahmoudd/pdf-squeeze/blob/master/packaging/INSTALL-LINUX.md).

macOS binaries are withheld pending resolution of Apple SDK-derived binding and
notice questions. Windows/Linux publication does not clear macOS.

Use `SHA256SUMS.txt` from this release to check downloaded archives. Each archive contains an `INSTALL.md`, the project's MIT `LICENSE` for original code and documentation, `THIRD_PARTY_NOTICES.md`, `LICENSING.md`, and the supporting third-party notices. Dependencies retain their own terms. Ghostscript is a separate required installation; see the [official Ghostscript downloads](https://ghostscript.com/releases/gsdnld.html). It is not included in these packages.

Extract your platform's archive and follow its `INSTALL.md`. Install Ghostscript first, then restart PDF Squeeze. On Windows, `gswin64c` must be on `PATH`; on Linux, `gs` must be on `PATH`.

Open the app with no arguments for the GUI. For CLI use, run `pdf-squeeze input.pdf --output result.pdf` (or `pdf-squeeze.exe` on Windows). Without `--output`, the app writes `<input_stem>_squeezed.pdf` beside the input.

Compression results vary. The `/ebook` profile can change image quality and other PDF properties; inspect your output. Already optimized or mostly vector PDFs may not shrink.

The Linux binary is built on Ubuntu 22.04; compatibility with other distributions is not guaranteed. The Linux GUI needs compatible desktop libraries, a graphical X11 or Wayland session, and a file-dialog backend (XDG desktop portal or Zenity). See each archive's `INSTALL.md` before use. Ghostscript's separate licensing terms should be reviewed for the intended use.

## Highlights

- Desktop file picker, progress state, and file-size savings summary.
- CLI mode with the same single-pass compression engine.
- Windows release builds open the desktop app without a console window and suppress Ghostscript console popups.
- Native packages for Windows x64 and Linux x64.
- Platform application icons and bundled third-party licensing documentation.

Source, issues, and release information: [PDF Squeeze on GitHub](https://github.com/mostafaamahmoudd/pdf-squeeze).

Automated native checks cover extracted CLI compression and GUI worker behavior;
an interactive GUI session is not exercised by CI. This is an experimental release.
The [platform licensing determination](https://github.com/mostafaamahmoudd/pdf-squeeze/blob/v0.1.0/docs/platform-publication.md)
records the reviewed notices and separate-program Ghostscript assessment.
