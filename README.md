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
