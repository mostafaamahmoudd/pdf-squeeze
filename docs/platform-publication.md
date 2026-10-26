# v0.1.0 Windows and Linux distribution determination

Review date: 2026-10-26. Baseline: master
`252333ebeb187a8662d14c98f087210b96d9f345`. This is a documented release decision
based on available technical and license evidence, not a legal opinion or a
project-specific assurance from Artifex. A formal lawyer's letter is not an
automatic release requirement.

## Decision and scope

The evidence supports publishing **Windows x64 (MSVC)** and **Linux x64 (GNU,
built on Ubuntu 22.04)** application-only archives. No substantiated unmet
redistribution obligation was identified for that scope after the notice review
below. This decision depends on the unchanged external-program integration,
reviewed default-feature dependency trees, complete accompanying notices, and
native CI verification. macOS binaries are **not approved for publication**.
All 13 unresolved inventory records and all existing notice bytes are preserved.

`third_party/publication-policy.json` binds this decision to the Cargo manifest,
lockfile, complete inventory, supplemental notices, font metadata, Ghostscript
integration, build script and additional runtime notices with SHA-256 hashes.
It lists exact active package versions for each approved target and the selected
license options for their exact declared expressions. It is a reviewed snapshot,
not a general license allowlist. Updating the snapshot requires a new review.
The original inventory expressions remain verbatim; options selected for this
release do not change any upstream license.

## Reproducible platform applicability

Using Cargo 1.89.0, after `cargo fetch --locked`, run:

```sh
cargo tree --locked --offline --target x86_64-pc-windows-msvc --edges normal,build --prefix none --format '{p}'
cargo tree --locked --offline --target x86_64-unknown-linux-gnu --edges normal,build --prefix none --format '{p}'
```

These are the default-feature trees used by the native release builds, including
build dependencies and procedural macros, excluding dev-only edges. The Linux-host Windows inspection has 144 unique third-party package versions.
The native Windows build additionally uses winres 0.1.12 and toml 0.5.11, for
146; Linux has 269, and the native union has 292. winres has its original MIT
notice; toml offers MIT/Apache-2.0 with both original texts retained (MIT selected).
[Cargo's host build-dependency rules](https://doc.rust-lang.org/cargo/reference/specifying-dependencies.html#build-dependencies)
mean cross-target trees can omit host-conditioned dependencies. The policy pins
both Linux-host and native-Windows inspection trees, and always checks the full
native obligations scope. Actual native Windows CI must match the native snapshot
before publication. The Linux-host publish job rechecks the cross-host tree and
all 146 native Windows packages' notice evidence; it does not infer native
completeness from the cross-host tree alone.
The broader 429-package metadata inventory deliberately includes inactive and
optional dependencies. Its conservative platform labels are not used to waive
issues. A Cargo tree is not a linker map; using every active build/normal package
as the compliance scope over-includes build-only code rather than guessing what
survives linking. Native jobs and the publication job recompute these trees and
reject any difference from the reviewed versions.

| Unresolved exact record | Windows x64 | Linux x64 | macOS default-feature trees |
| --- | --- | --- | --- |
| block 0.1.6 | inactive | inactive | inactive |
| block2 0.6.2 | inactive | inactive | active |
| dispatch 0.2.0 | inactive | inactive | active |
| dispatch2 0.3.1 | inactive | inactive | active |
| hexf-parse 0.2.1 | inactive | inactive | inactive |
| malloc_buf 0.0.6 | inactive | inactive | inactive |
| objc2 0.6.5 | inactive | inactive | active |
| objc2-app-kit 0.3.2 | inactive | inactive | active |
| objc2-core-foundation 0.3.2 | inactive | inactive | active |
| objc2-core-graphics 0.3.2 | inactive | inactive | active |
| objc2-encode 4.1.0 | inactive | inactive | active |
| objc2-foundation 0.3.2 | inactive | inactive | active |
| objc2-io-surface 0.3.2 | inactive | inactive | inactive |

None of these 13 records applies to the Windows/Linux application dependency
scope. Their historical evidence gaps are not resolved by that observation.
In particular, no standard MIT text or later upstream grant is substituted for
the missing historical notices. The Apple SDK-derived binding question remains
open; both macOS targets have nine active unresolved records. Original source
hashes, upstream revision links, and scope documents remain in LICENSING.md,
inventory.json and supplemental.json.

## Applicable terms and mandatory accompanying material

The primary evidence is the exact-version license and notice material under
`third_party/licenses` and `third_party/upstream`, with its immutable provenance
and hashes in inventory.json and supplemental.json. The release chooses MIT
where offered, Apache-2.0 for Apache-only components and moxcms/pxfm, and retains
all supplied alternatives and additional component notices. Historical slash
expressions in downcast-rs, scoped-tls, version_check, winapi, toml 0.5.11 and pollster have
both original MIT and Apache texts; selecting MIT here is an explicit reviewed
option, not an inventory parser rewriting their declarations. No active package
requires GPL, AGPL or LGPL terms. The LGPL alternatives elsewhere in the locked
inventory are not mandatory grants for these trees.

| Active grant/resource | Redistribution requirements and how this release meets them |
| --- | --- |
| MIT, including Windows crates and selected dual-license options | Include upstream copyright and permission/warranty notices with copies/substantial portions. All recovered exact-version texts are retained in every archive; project LICENSE is retained separately. |
| Apache-2.0 (12 Apache-only packages, plus selected moxcms/pxfm; dpi also requires MIT) | Include license; preserve pertinent copyright, patent, trademark and attribution notices and any supplied NOTICE; mark modifications if any. Dependencies are built from unchanged locked sources. All collected notices, AUTHORS, dpi's libm MIT notice and AccessKit's Chromium BSD notice are retained. No endorsement or trademark permission is asserted. |
| BSD-2-Clause (arrayref), BSD-3-Clause (tiny-skia and tiny-skia-path; additional Chromium terms) | Binary documentation must reproduce copyright, conditions and disclaimer; preserve non-endorsement restrictions. Original texts ship with archives. |
| ISC (libloading) | Retain copyright and permission notice, including disclaimer. Original LICENSE ships. |
| Zlib (foldhash) | Do not misrepresent origin; mark altered source; preserve notice in source distributions. Dependency source is unchanged; original notice is included conservatively with binaries too. |
| BSL-1.0 (clipboard-win, error-code) | Copyright and license inclusion exception applies to solely machine-executable object code. Full original notices are nevertheless included. |
| Unicode-3.0 (18 packages; also required with MIT for unicode-ident) | Copyright and permission must accompany data/software or documentation; preserve disclaimers and restrictions on promotion using holders' names. The original license files, including ICU/IBM notices, ship. |
| Hack font | Source Foundry MIT, Bitstream Vera copyright/trademark/permission and DejaVu public-domain statement ship in Hack-Regular.txt. No font modification, standalone font sale or reserved-name reuse. |
| Noto Emoji and Linux Cantarell | OFL-1.1, original copyrights and reserved names remain with fonts. OFL texts and original embedded name records in fonts.json ship. No font modification, standalone sale or endorsement. Cantarell's recovered provenance remains explicit. |
| Ubuntu font | Ubuntu Font Licence 1.0 and original copyright/name records ship. Font retains its original name and license; embedding does not relicense the application. |
| emoji-icon-font | Original John Slegers MIT notice ships. |
| Rust standard library/runtime | The Rust 1.89.0 official toolchain's original COPYRIGHT-library.html and license directory are added under third_party/rust-1.89.0, including additional component notices and exceptions. They supplement, rather than replace, the Cargo inventory. |
| Project code and icon | Owner-approved MIT LICENSE for original code/docs and separately recorded distribution approval for the generated icon remain in LICENSING.md. No exclusive icon rights or upstream copyright holders are invented. |

The resolved wgpu-hal pointer evidence remains intact even though that optional
backend is inactive in these default trees. Every notice pointer is recomputed;
affected active packages cannot publish with unresolved pointers even if an
issue string is cleared. Every collected file, including inactive/macOS evidence,
is checked for existence, nonemptiness and original hash, then byte-compared in
the final archives. The archives retain the full inventory/notice superset.

OS-provided libraries are not copied into archives. Linux `ldd` checks for missing
libraries and unintended Ghostscript linkage; system glibc/graphics libraries
remain installed by the OS. Windows uses the MSVC target and OS runtime rather
than shipping a compiler, SDK, or Ghostscript DLL. This decision does not approve
future bundling of any system runtime or installer.

## Ghostscript: facts, terms, assessment and remaining uncertainty

`src/gs.rs` executes the user's separately installed `gs` or `gswin64c` using
`std::process::Command`. It checks `--version` and invokes the ordinary `pdfwrite`
command-line interface with `/ebook` settings and input/output PDF paths. PDF
Squeeze reads the produced PDF as a standard document, process exit status and
stdout/stderr diagnostics. There is no libgs linking, Ghostscript source, plugin,
internal API, shared memory, private data structure exchange or modified
Ghostscript. The app has no network service. Packaging copies only the built
application, approved icons and documentation. CI installs Ghostscript for tests;
its executable, libraries, resources, installer and source are not release assets.

The [AGPLv3 text, sections 0 and 2](https://www.gnu.org/licenses/agpl-3.0.en.html)
distinguishes running an unmodified program from conveying copies. Sections 4–6
set notice, license and Corresponding Source obligations for covered works that
are conveyed. Section 5 addresses combined works and aggregates. Section 13
addresses modified programs offering remote network interaction. If a future
release conveys Ghostscript or forms a covered combined work, it must satisfy
the applicable AGPL obligations (including the whole-work licensing/source
requirements where triggered) or obtain appropriate commercial rights; simply
publishing this MIT repository is not a substitute for that compliance.

The [GNU GPL FAQ on aggregation](https://www.gnu.org/licenses/gpl-faq.en.html#MereAggregation)
explains that command-line/pipes communication normally connects separate
programs, but semantics, including exchange of complex internal structures, can
change the conclusion. This is FSF guidance, not an Artifex permission or a court
ruling. [Artifex's FAQ](https://ghostscript.com/faq/) permits unchanged,
non-redistributed AGPL installations and requires careful review when
distributing Ghostscript; it also cautions about embedding and applications
using Ghostscript. Its [licensing page](https://artifex.com/licensing/) presents
AGPL and commercial choices; its [AGPL text](https://artifex.com/licensing/gnu-agpl-v3)
provides the operative conditions. Broad website descriptions do not resolve the
copyright boundary for this particular application.

**Assessment/inference:** The ordinary file/CLI boundary, independently installed
unmodified executable, absence of Ghostscript code in the distributed app, and
absence of intimate internal communication support treating these as separate
programs. On that evidence, this application-only Windows/Linux distribution
does not convey Ghostscript or identify an unmet Ghostscript notice, source-offer
or commercial-license obligation. That is sufficient for this scoped release;
it is not an automatic subprocess exemption or a guarantee of a legal outcome.
Artifex has not supplied a project-specific determination, and courts ultimately
decide derivative/combined-work questions. Any contrary project-specific evidence,
Ghostscript bundling, linking, private protocol, modifications or network-service
use requires reassessment before the affected distribution. Users obtain
Ghostscript from its own distributor under its own terms.

## Publication enforcement

Run `python3 scripts/verify_licenses.py --require-publishable --platform windows-x64`
and the equivalent for `linux-x64`, using Rust 1.89.0 and all locked sources.
Add `--archive` with the exact corresponding archive name for final verification.
Scoped publication rejects missing project license, review-input/tree drift,
unknown grants, missing active terms, active issues and unresolved active pointers.
It still checks all preserved evidence bytes. Without `--platform`, strict
`--require-publishable` still rejects the 13 global issues. macOS scoped publication
is explicitly rejected. No all-target clearance is asserted.

The guarded version tag must match Cargo metadata and be an ancestor of updated
master. Both native jobs must pass format, compilation, tests including real
Ghostscript/worker integration, Clippy, release build, packaging and extracted
CLI checks. Publication verifies each scoped archive, generates and verifies
SHA256SUMS.txt, creates a draft with exactly two archives plus checksums, then
makes it public. Verify the actual public downloads against that manifest and
the GitHub asset digests. No manually substituted local binary is publishable.
The automated checks do not exercise an interactive GUI session; that limitation
is disclosed for this experimental release.
