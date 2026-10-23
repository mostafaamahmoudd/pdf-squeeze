# v0.1.0 release readiness

This is a working review record, not permission to publish. The release workflow's
project `LICENSE` and unresolved-inventory guards remain in force. Do not create
a `v0.1.0` tag or publish a Release until the decisions below are closed and all
four native archives have been checked.

## Locked dependency scope

The current `Cargo.lock` has 13 unresolved licensing entries. A default-feature
`cargo tree --locked --offline --target <triple> --edges normal,build` review
found the following active paths:

| Target triple | Unresolved entries with active dependency paths |
| --- | ---: |
| `x86_64-pc-windows-msvc` | 0 |
| `x86_64-unknown-linux-gnu` | 0 |
| `aarch64-apple-darwin` | 9 |
| `x86_64-apple-darwin` | 9 |

Both macOS targets have paths to `dispatch 0.2.0`, `block2 0.6.2`,
`dispatch2 0.3.1`, `objc2 0.6.5`, `objc2-app-kit 0.3.2`,
`objc2-core-foundation 0.3.2`, `objc2-core-graphics 0.3.2`,
`objc2-encode 4.1.0`, and `objc2-foundation 0.3.2`.

`block 0.1.6`, `malloc_buf 0.0.6`, `hexf-parse 0.2.1`, and
`objc2-io-surface 0.3.2` have no active default-feature path in those four
target trees. Cargo's dependency tree is not a binary linker map. The
conservative inventory, its 13 unresolved issues, and the publication gate
remain unchanged. Every planned archive carries the same inventory and notice
superset.

The macOS paths run through several GUI and dialog dependencies, including
`eframe`/`winit`, `glutin`, `arboard`, and `rfd`. Replacing one dialog crate
would not remove all nine active gaps. No upgrade has been established as
clearing them; a proposed upgrade needs a fresh locked inventory, source and
notice review, and native macOS builds before it can be accepted.

## Owner decisions recorded

The owner approved `Copyright (c) 2026 Mostafa Mahmoud` and the standard
[MIT License](../LICENSE) for original application source code, GUI, CLI,
build scripts, and original project documentation to the extent of their
rights. Third-party dependencies and assets retain their own terms.

The owner approved this icon provenance statement:

> The selected blue-and-red PDF compression-press icon was generated using
> ChatGPT for pdf-squeeze. The source image is
> `assets/icons/pdf-squeeze-icon.png`; the Windows, Linux and macOS icon assets
> were derived from it. The project owner approves distributing the icon and
> its derived assets with pdf-squeeze v0.1.0. This does not assert exclusive
> rights or automatically place the artwork under the project's MIT License.

## Decisions required before publication

1. **Third-party dependencies:** Obtain version-applicable notice evidence or
   independent compliance review for the 13 inventory issues, especially the
   nine active macOS paths and the Apple SDK-derived code noted in
   [LICENSING.md](../LICENSING.md). Do not clear an inventory issue solely
   because its crate is absent from a target's active Cargo tree.
2. **Ghostscript:** Review the planned external-process integration and
   distribution against Ghostscript's AGPL/commercial terms. Ghostscript is
   not bundled. This document does not decide that question.
3. **macOS distribution:** Decide whether unsigned, unnotarized app bundles
   meet the intended public-release standard. If signed distribution is
   required, arrange Developer ID signing, notarization, and validation on
   both Apple Silicon and Intel Macs.

## Final technical checks

- Run the locked Rust format, check, test, Clippy, and release-build commands.
- Run every Python licensing test, `license_inventory.py --check`, and
  `verify_licenses.py`. The `--require-publishable` gate must pass after the
  remaining third-party decisions are implemented; it currently fails by
  design because 13 inventory entries remain unresolved.
- Run the four native GitHub Actions jobs on the exact candidate commit.
  Inspect executable architecture, branding, Ghostscript discovery, archive
  instructions, notice bytes, and CLI smoke tests. The GUI needs an interactive
  check on each intended platform.
- Verify the published archives against `SHA256SUMS.txt` generated from those
  exact artifacts. Do not reuse a checksum from a local or earlier build.
- Review [release notes](../packaging/RELEASE_NOTES.md) and the
  [launch announcement](launch-announcement.md) before publication.
