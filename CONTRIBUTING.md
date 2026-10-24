# Contributing to PDF Squeeze

Thanks for helping improve PDF Squeeze. Bug fixes, performance improvements, documentation, and cross-platform compatibility work are all welcome.

## Report a bug or suggest a feature

Search [GitHub Issues](https://github.com/mostafaamahmoudd/pdf-squeeze/issues) first. For a bug, include your operating system and architecture, PDF Squeeze and Ghostscript versions, steps to reproduce it, and what you expected to happen. Include error messages and a small sample PDF if you can share one safely. Remove personal or confidential information before posting files or logs.

For a new feature, open an issue explaining the problem and how the feature would help. Discuss substantial changes before starting so we can agree on an approach.

## Set up a development environment

Install Rust through [rustup](https://rustup.rs/) and Python 3.10 or later for the packaging tests. CI uses Rust 1.89.0 with the `rustfmt` and `clippy` components. If needed, install that toolchain with:

```sh
rustup toolchain install 1.89.0 --component rustfmt --component clippy
```

If your default Rust toolchain differs from CI, use `cargo +1.89.0` in place of `cargo` in the commands below.

The [README's build instructions](README.md#build-from-source) cover native build tools and Linux desktop libraries.

Install Ghostscript separately; it is not bundled. Use `brew install ghostscript` on macOS, `choco install ghostscript` on Windows, or `sudo apt install ghostscript` on Ubuntu/Debian. Check `gs --version` on Linux/macOS or `gswin64c --version` on Windows. Linux and Windows need it on `PATH`; macOS also checks the usual Homebrew locations. Restart the app after installation.

Fork the repository on GitHub, then clone your fork and create a branch:

```sh
git clone https://github.com/YOUR-USERNAME/pdf-squeeze.git
cd pdf-squeeze
git switch -c fix/describe-the-bug
cargo build --locked
```

Use a short branch name with a prefix such as `fix/`, `feat/`, `perf/`, `docs/`, or `chore/`. Keep each branch focused on one change.

## Checks before a pull request

Run these from the repository root:

```sh
cargo fmt --check
cargo check --locked
cargo test --locked
cargo test --locked -- --ignored
cargo clippy --locked --all-targets -- -D warnings
python3 -m unittest discover -s tests -p 'test_*.py'
```

The ignored Rust tests require Ghostscript and exercise integration and GUI-worker behavior; they do not replace interactive GUI testing. On Windows, use `python` if that is your Python command. For documentation-only changes, check links and run the Python tests, which verify the packaged README across all four release layouts.

## Submit a pull request

Explain the problem, your change, and the checks you ran. Link a related issue if there is one, and mention which platforms you tested and anything you could not verify. Add or update tests when behavior changes. Small, focused pull requests are easier to review.

Use concise, one-line Conventional Commit messages, for example `fix: handle unreadable PDFs`, `perf: reduce temporary file copies`, or `docs: clarify Linux setup`.

Maintainers review contributions before merging and may ask for changes. Questions are welcome in the issue or pull request discussion.

The project's [MIT License](LICENSE) covers original application code and documentation. The icon and dependencies have separate terms, and some licensing questions remain unresolved; see [LICENSING.md](LICENSING.md) and [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md). Keep those notices and release safeguards intact when changing dependencies or packaging.
