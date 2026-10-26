# PDF Squeeze

<img src="assets/icons/pdf-squeeze-icon.png" alt="PDF Squeeze app icon" width="96">

PDF Squeeze is a desktop app and command-line tool for making one PDF smaller. It runs one Ghostscript conversion with the `/ebook` profile. The GUI and CLI share the same compression engine. Ghostscript is installed separately; it is not bundled with the app.

## Features

- Choose input and output files in the desktop window, or pass paths on the command line.
- Run one compression pass in a background worker so the desktop window stays responsive.
- Validate the result before saving it. If it is not smaller, save an unchanged copy of the original.
- Report original and output sizes, savings, elapsed time, and the profile used.
- Protect the input and refuse to replace an existing output file.

In one real-world Windows test, an **80 MB PDF became 17 MB**. That is one example, not a size or quality guarantee: results depend on the PDF, and the `/ebook` profile can change image quality and other properties. Already optimized or mostly vector PDFs may not shrink.

## Downloads

v0.1.0 publication is limited to Windows x64 and Linux x64. Get release archives from [GitHub Releases](https://github.com/mostafaamahmoudd/pdf-squeeze/releases):

| Platform | Archive | Included app |
| --- | --- | --- |
| Windows x64 | `pdf-squeeze-windows-x64.zip` | `pdf-squeeze.exe` |
| Linux x64 | `pdf-squeeze-linux-x64.tar.gz` | `pdf-squeeze` and desktop launcher assets |

macOS binary publication is on hold pending resolution of Apple SDK-derived
binding and notice questions. macOS build and packaging code remains available
for development; it is not distribution clearance.

Each archive includes `INSTALL.md`, the project `LICENSE`, and third-party licensing documentation. Verify downloads against `SHA256SUMS.txt` from the same release. Current release-readiness decisions are tracked in [release review](https://github.com/mostafaamahmoudd/pdf-squeeze/blob/master/docs/release-readiness.md).

## Install Ghostscript

On Linux, Ghostscript must be available as `gs` on `PATH`; on Windows, as `gswin64c` on `PATH`. On macOS, PDF Squeeze also checks the common Homebrew locations `/opt/homebrew/bin/gs` and `/usr/local/bin/gs` when `PATH` does not contain `gs`. Restart PDF Squeeze after installing it.

| OS | Command |
| --- | --- |
| macOS | `brew install ghostscript` |
| Windows | `choco install ghostscript` |
| Ubuntu/Debian Linux | `sudo apt install ghostscript` |

Ghostscript is installed separately and is not included in any release archive. Check its availability with `gs --version` on Linux/macOS or `gswin64c --version` on Windows. See its [AGPL and commercial licensing options](https://ghostscript.com/licensing/) and our [application-only distribution assessment](https://github.com/mostafaamahmoudd/pdf-squeeze/blob/master/docs/platform-publication.md).

## Install and use

Extract the archive and follow its `INSTALL.md`: [Windows](https://github.com/mostafaamahmoudd/pdf-squeeze/blob/master/packaging/INSTALL-WINDOWS.md), [Linux](https://github.com/mostafaamahmoudd/pdf-squeeze/blob/master/packaging/INSTALL-LINUX.md), or [macOS](https://github.com/mostafaamahmoudd/pdf-squeeze/blob/master/packaging/INSTALL-MACOS.md). Install Ghostscript first, then restart PDF Squeeze. Launch the app without arguments to open the GUI. Pick an input PDF, choose an output path, and click **Compress**.

The application icon comes from [`assets/icons/pdf-squeeze-icon.png`](https://github.com/mostafaamahmoudd/pdf-squeeze/blob/master/assets/icons/pdf-squeeze-icon.png). Windows, Linux, and macOS icon assets are checked in.

## Build from source

Install Rust and Cargo, Ghostscript, and your platform's native build tools. On Ubuntu or Debian, the GUI needs X11/Wayland development libraries and a file-dialog backend:

```sh
sudo apt install build-essential libxcb-render0-dev libxcb-shape0-dev libxcb-xfixes0-dev libxkbcommon-dev libssl-dev zenity
```

On macOS, install Xcode Command Line Tools. On Windows, install the Microsoft C++ Build Tools with the Desktop development workload. Build and launch locally with:

```sh
cargo build --release --locked
cargo run --release --locked
```

The executable is `target/release/pdf-squeeze` on Linux/macOS or `target\release\pdf-squeeze.exe` on Windows. Official release archives are built on their native platforms.

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

## Limitations and licensing

- The `/ebook` profile can change image quality and other PDF properties. Check the output before relying on it.
- Linux archives are built on Ubuntu 22.04; compatibility with other distributions is not guaranteed.
- macOS binaries are withheld while distribution rights remain unresolved.
- Ghostscript must be installed separately under its own licensing terms. It is not bundled or linked.

PDF Squeeze is open source and released under the [MIT License](LICENSE) for its original application code and documentation.

The application icon and third-party dependencies have their own licensing terms. See [LICENSING.md](LICENSING.md) and [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md) for details.

The dependency inventory preserves 13 unresolved licensing entries. None is active
in the reviewed Windows/Linux release trees. See the [scoped release determination](https://github.com/mostafaamahmoudd/pdf-squeeze/blob/master/docs/platform-publication.md)
for applicable terms, Ghostscript assessment and remaining macOS questions.

## Tests

```sh
cargo test --locked
cargo fmt --check
cargo clippy --locked --all-targets -- -D warnings
```

The ignored GUI-worker and integration tests use small temporary PDFs and require Ghostscript installed:

```sh
cargo test --locked -- --ignored
```

## Contributing

Contributions are welcome: bug fixes, performance improvements, documentation, and better support across Windows, Linux, and macOS. Have an idea for a new feature? Start with a [GitHub Issue](https://github.com/mostafaamahmoudd/pdf-squeeze/issues) so we can discuss it together.

1. Fork the repository and clone your fork.
2. Create a branch for your change, such as `fix/describe-the-bug` or `docs/improve-setup`.
3. Make your changes and run the [relevant checks](CONTRIBUTING.md#checks-before-a-pull-request).
4. Submit a pull request explaining what changed, why, and how you tested it.

Maintainers review pull requests before merging and may suggest changes. See [CONTRIBUTING.md](CONTRIBUTING.md) for setup instructions, bug reports, and pull request guidance.
