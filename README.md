# PDF Squeeze

`pdf-squeeze` is a small cross-platform desktop tool for reducing one PDF without going below a 72 DPI image-quality floor. It runs Ghostscript as a subprocess and searches image resolutions from 72 to 300 DPI. The GUI and CLI use the same compression code. No PDF is loaded into memory: the app checks the file header, then Ghostscript reads the file, and output sizes come from file metadata.

PDF Squeeze keeps the smallest Ghostscript result it measures, then compares it with the input. If Ghostscript made a smaller file, that result is saved. If the input is smaller or the same size, an unchanged copy is saved and the app reports that compression did not help. This matters for PDFs that are already optimized or mostly vector text and drawings. The search stops when its DPI bounds differ by at most 5; Ghostscript output size is not perfectly monotonic, so the result is the smallest measured candidate rather than a guaranteed global minimum.

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

Launch the executable without arguments. The window starts in light mode. Choose an input PDF and output path, then click **Compress**. The app remains responsive while Ghostscript runs. The progress bar advances after each Ghostscript iteration; a single step may take a while for a large file. A missing Ghostscript installation appears as a warning in the window and disables compression.

## CLI

Pass an input path to use CLI mode. Reported MB means 1,000,000 bytes.

```sh
pdf-squeeze input.pdf -o output.pdf
pdf-squeeze input.pdf
```

Without `-o`, the output is `<input_stem>_squeezed.pdf` beside the input. The CLI reports the original and final sizes and the DPI used when compression helps. If the input is already smaller, it reports that the original was kept. Both outcomes exit successfully. Invalid inputs, missing Ghostscript, and Ghostscript failures exit with an error.

PDF Squeeze will not replace an existing output file. Choose a new output path if the suggested name already exists.

## Tests

```sh
cargo test
cargo fmt --check
cargo clippy -- -D warnings
```

The ignored integration test uses a small PDF fixture and requires Ghostscript installed:

```sh
cargo test -- --ignored
```
