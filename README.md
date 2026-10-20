# PDF Squeeze

`pdf-squeeze` is a small cross-platform desktop tool for reducing one PDF with a single Ghostscript conversion using `-dPDFSETTINGS=/ebook`. The GUI and CLI use the same compression engine. The Rust wrapper reads only small validation buffers and file metadata; Ghostscript handles PDF processing and its memory requirements depend on the document.

PDF Squeeze validates the candidate before comparing its size with the input. If the candidate is smaller, it is saved. Otherwise, an unchanged copy of the original is saved. There is no automatic second pass or DPI search. The `/ebook` profile can change image quality and other PDF properties; it does not guarantee a particular file size or a resolution for all PDF content. Already optimized or mostly vector documents may not shrink.

## Install Ghostscript

Ghostscript must be available on `PATH` as `gs` on macOS/Linux or `gswin64c` on Windows. Restart PDF Squeeze after installing it.

| OS | Command |
| --- | --- |
| macOS | `brew install ghostscript` |
| Windows | `choco install ghostscript` |
| Ubuntu/Debian Linux | `sudo apt install ghostscript` |

On Linux, building the native GUI may also require:

```sh
sudo apt install libxcb-render0-dev libxcb-shape0-dev libxcb-xfixes0-dev libxkbcommon-dev libssl-dev
```

### Windows Quick Start (pre-built binary)

1. Install Ghostscript from https://ghostscript.com/releases/gsdnld.html (choose the 64-bit Windows installer).
2. Unzip the `pdf-squeeze` folder to a location of your choice.
3. Double-click `pdf-squeeze.exe`. The GUI opens with no arguments.
4. Select a PDF, pick an output path, and click Compress.

If the app shows a warning that Ghostscript was not found, re-run the Ghostscript installer and make sure the "Add to PATH" option is selected. Then restart the app.

## Building from Source

### Ubuntu 24.04 (Linux)

```bash
# Install build tools and GUI system dependencies
sudo apt update
sudo apt install -y build-essential libxcb-render0-dev libxcb-shape0-dev libxcb-xfixes0-dev libxkbcommon-dev libssl-dev zenity

# Install Rust via rustup
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh

# Activate the environment
source "$HOME/.cargo/env"
```

`eframe` requires the `libxcb-*` and `libxkbcommon-dev` packages on Linux; `zenity` is required for native file dialogs via `rfd`, and without it the file picker will not open.

### macOS

```bash
# Install Xcode Command Line Tools if not already present
xcode-select --install

# Install Rust via rustup
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh

# Activate the environment
source "$HOME/.cargo/env"
```

Ghostscript can be installed via `brew install ghostscript`.

### Windows

```powershell
# Install Rust via winget (recommended by Microsoft)
winget install Rustlang.Rustup
```

Windows requires the **Microsoft C++ Build Tools** with the "Desktop development with C++" workload (the Community edition is free for individuals); alternatively, download and run `rustup-init.exe` from https://rust-lang.org/tools/install, and if `cargo` is not found after installation, restart the terminal or verify that `%USERPROFILE%\.cargo\bin` is on PATH.

### Building a Windows binary from Linux (best effort)

If you are on Linux and want to produce a Windows `.exe` without a Windows machine:

```bash
rustup target add x86_64-pc-windows-gnu
sudo apt install -y mingw-w64
cargo build --release --target x86_64-pc-windows-gnu
```

The binary will be at `target/x86_64-pc-windows-gnu/release/pdf-squeeze.exe`.

**Caveat:** `eframe` and GUI dependencies may fail to cross-compile cleanly from Linux to Windows depending on the toolchain and crate versions. If this build fails, build on a real Windows machine or a Windows VM instead. Cross-compilation is not the supported path for releases.

### Verification (all OS)

```bash
cargo --version
rustc --version
```

### Build and run

```bash
cargo build --release
cargo run --release
```

The release binary will be at `target/release/pdf-squeeze` (Linux/macOS) or `target\release\pdf-squeeze.exe` (Windows).

## Build

Install Rust with Cargo, then run:

```sh
cargo build --release
```

The executable is `target/release/pdf-squeeze` (or `target/release/pdf-squeeze.exe` on Windows).

## GUI

Launch the executable without arguments. The window starts in light mode. Choose an input PDF and output path, then click **Compress**. Compression runs on a worker thread. A spinner and stage label show activity without estimating a completion percentage. Results show original/output sizes, percentage saved, profile, elapsed job time, and compression pass count. A missing Ghostscript installation appears as a warning in the window and disables compression.

## CLI

Pass an input path to use CLI mode. Reported MB means 1,000,000 bytes.

```sh
pdf-squeeze input.pdf -o output.pdf
pdf-squeeze input.pdf
```

Without `-o`, the output is `<input_stem>_squeezed.pdf` beside the input. The CLI reports original/output sizes, percentage saved, profile, elapsed job time, and compression pass count. If the valid candidate is not smaller, it reports that the original was kept and an unchanged copy was saved. Both outcomes exit successfully. Invalid inputs, missing Ghostscript, fatal Ghostscript diagnostics, and malformed candidate outputs exit with an error.

PDF Squeeze will not replace an existing output file. Choose a new output path if the suggested name already exists.

## Tests

```sh
cargo test
cargo fmt --check
cargo clippy -- -D warnings
```

The ignored GUI-worker and integration tests use small temporary PDFs and require Ghostscript installed:

```sh
cargo test -- --ignored
```
