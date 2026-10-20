# PDF Squeeze

`pdf-squeeze` is a small cross-platform desktop tool for reducing one PDF to a target size. It runs Ghostscript as a subprocess and searches image resolutions from 50 to 300 DPI. The GUI and CLI use the same compression code. No PDF is loaded into memory: the app checks the file header, then Ghostscript reads the file, and output sizes come from file metadata.

PDFs made mostly of vector text and drawings may not shrink much when image DPI is lowered. If the original already fits the target, PDF Squeeze saves it unchanged. Otherwise, if even 50 DPI is above the target, PDF Squeeze saves that result anyway and warns you. The search stops within 5 DPI of the size boundary; because Ghostscript output size is not perfectly monotonic, this is a practical approximation rather than a global quality guarantee.

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

## Build

Install Rust with Cargo, then run:

```sh
cargo build --release
```

The executable is `target/release/pdf-squeeze` (or `target/release/pdf-squeeze.exe` on Windows).

## GUI

Launch the executable without arguments. Choose an input PDF, set the target size in MB (default: 50), choose an output path, and click **Compress**. The app remains responsive while Ghostscript runs. A missing Ghostscript installation appears as a warning in the window and disables compression.

## CLI

Pass an input path to use CLI mode. MB means 1,000,000 bytes.

```sh
pdf-squeeze report.pdf
pdf-squeeze report.pdf --target-mb 12.5
pdf-squeeze report.pdf -t 20 -o smaller.pdf
```

Without `-o`, the output is `<input_stem>_squeezed.pdf` beside the input. The CLI prints the final size and DPI used, or says that no DPI change was needed when it preserves the original. An unreachable target produces a warning, saves the 50 DPI result, and exits successfully. Invalid inputs, bad target values, missing Ghostscript, and Ghostscript failures exit with an error.

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
