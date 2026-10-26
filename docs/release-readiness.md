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

## 2026-10-26 licensing reassessment

The 13 entries are evidence gaps, not 13 demonstrated license conflicts.
Cargo's `license` field is a published SPDX license declaration, but it is not
a substitute for accompanying license terms or any copyright notice supplied
by a rights holder. The original inventory issues and collected notices remain
intact. This review does not certify legal compliance.

| Exact locked versions | Declaration and evidence gap | Default-feature applicability |
| --- | --- | --- |
| `block 0.1.6`, `dispatch 0.2.0`, `malloc_buf 0.0.6` | MIT declared; no version-applicable license or copyright text recovered | `dispatch` is active on both macOS targets; `block` and `malloc_buf` have no active path in the four reviewed target trees |
| `hexf-parse 0.2.1` | CC0-1.0 declared; no version-applicable dedication text recovered | No active path in the four reviewed target trees |
| `block2 0.6.2`, `dispatch2 0.3.1`, `objc2 0.6.5`, `objc2-app-kit 0.3.2`, `objc2-core-foundation 0.3.2`, `objc2-core-graphics 0.3.2`, `objc2-encode 4.1.0`, `objc2-foundation 0.3.2`, `objc2-io-surface 0.3.2` | MIT or an option including MIT declared; exact-revision upstream scope documents are preserved, but contain no complete permission text or copyright notice | All except `objc2-io-surface` are active on both macOS targets; `objc2-io-surface` has no active path in the four reviewed target trees |

The exact versions, archive/source hashes, and upstream findings are recorded in
[LICENSING.md](../LICENSING.md). No mandatory GPL-only or AGPL-only Rust crate
expression was found in the locked inventory. Target dependency paths do not
prove what code survived linking, so the archives retain the full notice
superset. No missing copyright holder is inferred from a crate's author field.

A proportionate publication policy can accept a version-specific upstream SPDX
grant without an upstream copy of a standard license text **only when** the
applicable canonical terms are included in every archive, all supplied
copyright and attribution notices are preserved, and the evidence and selected
license option are recorded for that exact version. It must still fail for an
undeclared or incompatible grant, an unresolved notice pointer, a missing
mandatory notice or permission term, or a substantiated distribution restriction.
The [MIT and CC0 reference texts](../third_party/license-terms/README.md) are
now included with packaging inputs, with pinned SPDX sources and SHA-256
provenance. They do not invent missing upstream copyright notices or resolve
the remaining legal questions.
The existing `--require-publishable` check remains unchanged until those
conditions have been implemented and verified. Missing historical files alone
should not be silently converted into invented upstream notices.

The separate Ghostscript question remains material. `src/gs.rs` starts an
external `gs` or `gswin64c` process and the packaging script does not include
Ghostscript. Users install it separately. [Artifex's FAQ](https://ghostscript.com/faq/)
says an unchanged installation that is not redistributed can use the AGPL
release, but it does not determine whether this particular MIT application
must take AGPL terms or a commercial license. This review has not established
the applicable distribution terms for this integration, so it does not yet
authorize public binaries.

The [exact-version objc2 licensing document](https://github.com/madsmtm/objc2/blob/objc2-0.6.5/LICENSE.md)
states that some crates are derived from Apple SDKs and questions whether such
derived works may be distributed. The [Xcode and Apple SDKs Agreement](https://www.apple.com/legal/sla/docs/xcode.pdf)
allows distribution of qualifying macOS applications outside the App Store but
does not by itself resolve that derived-code question. Whether the included
generated bindings contain protected SDK expression that needs additional
permission remains undetermined for the macOS binaries.

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
