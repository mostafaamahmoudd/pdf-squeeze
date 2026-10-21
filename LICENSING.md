# Licensing evidence and outstanding review

This document records engineering evidence for release review. It does not make a
legal determination, select a license on behalf of an upstream author, or certify
that a binary distribution satisfies every obligation.

## Project license — owner decision required

Cargo.toml declares MIT. There is no verified root LICENSE file. The owner must
confirm the copyright holder, intended licensing scope and approved license text.
No project copyright statement or license grant has been created by this work.
Third-party notices do not license pdf-squeeze itself. The release workflow still
refuses publication without a nonempty root LICENSE; file presence is not proof
of ownership or approval.

## Locked Rust dependency inventory

[THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md) lists all 429 third-party packages in Cargo.lock and links collected license and
notice texts where recovered. 425 packages have at least one collected notice;
13 packages have explicitly recorded evidence gaps (four without texts, nine
with scope documents only). The inventory covers
the entire locked metadata graph, including optional and non-desktop packages,
not just crates proven to survive linking. Every platform receives the same
conservative superset. A listed dependency is not necessarily in a given binary.

[third_party/inventory.json](third_party/inventory.json) records declared license
expressions verbatim, versions, registries, repositories, upstream VCS revisions
when supplied, authors (not inferred copyright holders), incoming dependency
kinds and cfg conditions, per-platform graph roles, collected notice hashes and
candidate binary resources. The lockfile SHA-256 binds the inventory to this
resolution. No slash expression is silently converted into SPDX, and no OR
alternative is selected. LGPL alternatives and LLVM exceptions remain visible.
This inventory contains no crate declaring a mandatory GPL-only or AGPL-only
expression; that observation is not a binary-distribution legal conclusion.

Platform roles are computed by traversing Cargo's platform-filtered metadata,
excluding dev edges and marking build dependencies, proc macros and their
transitive dependencies as build paths. A crate can have both normal and build
paths. These are conservative graph labels, not a linker map. Cargo feature
unification, host build dependencies and optional dependencies can over-include
crates; the inventory must not be used to prove that a package is absent from a
binary. Rust toolchain/runtime components, operating-system libraries, SDKs and
other system dependencies are outside this crate inventory and still require
release review where applicable.

License, licence, copying, copyright, notice, authors, OFL, UFL and unlicense
files are collected recursively (excluding ordinary source-code filenames), along with font text notices and any explicit
Cargo license-file. Original bytes are preserved, including CRLF. This retains
upstream copyright and NOTICE texts without synthesizing holders. It is not an
exhaustive source-code-header or binary attribution audit. Resource discovery
records font, image, icon and shader-binary candidates, including test fixtures;
it does not assert that every candidate is shipped. Source shaders, generated
code, data tables and platform runtime artifacts need human review when changed.

Many published crate archives omit workspace-root license texts. Supplemental
files in [third_party/upstream](third_party/upstream) were retrieved from exact
upstream commits, normally those recorded by the crate's .cargo_vcs_info.json.
[third_party/supplemental.json](third_party/supplemental.json) records each URL,
SHA-256 and associated package versions. The winapi GNU import-library packages
lack VCS metadata; their texts were recovered from the upstream 0.3.9 revision,
which contains the version 0.4.0 architecture packages. Keep this provenance
qualification when reviewing those prebuilt import libraries.

Four packages still have **no recovered license/notice text**:

| Crate | Version | Declaration | Relevant graph paths | Outstanding evidence |
| --- | --- | --- | --- | --- |
| block | 0.1.6 | MIT | macOS | Published archive lacks license and copyright notice; historical upstream tag is 0.1.6. |
| dispatch | 0.2.0 | MIT | macOS | Archive and recorded upstream revision lack a standalone license text. |
| malloc_buf | 0.0.6 | MIT | macOS | Published archive lacks license and copyright notice. |
| hexf-parse | 0.2.1 | CC0-1.0 | All four targets' conservative graphs | Archive and recorded upstream revision lack a standalone dedication/license text. |

Their metadata has not been treated as a substitute for missing upstream texts.
Obtain authoritative notices or an appropriately reviewed resolution before
public distribution. The inventory flags these gaps, and publication checks fail
until they are resolved. The newer objc2 scope documents cover nine additional packages but contain no
complete license permission body or copyright notice: block2 0.6.2, dispatch2
0.3.1, objc2 0.6.5, objc2-encode 4.1.0, objc2-foundation 0.3.2, objc2-app-kit
0.3.2, objc2-core-foundation 0.3.2, objc2-core-graphics 0.3.2 and objc2-io-surface
0.3.2. These are preserved as **scope notices only**, with unresolved issues in
the inventory. The documents also explicitly raise questions about Apple
SDK-derived code; appropriate review is still needed. An older Steven Sheldon
MIT grant has not been assigned to these newer revisions. Finding at least one
notice for another crate does not prove all its obligations are covered.

## Embedded fonts and other resources

The four egui fonts are embedded by epaint_default_fonts 0.31.1. Its package-level
expression is `(MIT OR Apache-2.0) AND OFL-1.1 AND Ubuntu-font-1.0`; the individual
font notices contain additional detail that must be retained:

| Resource | Preserved upstream information | Texts |
| --- | --- | --- |
| Hack-Regular.ttf | Source Foundry Authors 2018; Bitstream 2003; DejaVu public-domain statement and reserved font names | [Hack notice](third_party/licenses/epaint_default_fonts-0.31.1/fonts/Hack-Regular.txt), including MIT and Bitstream Vera terms |
| NotoEmoji-Regular.ttf | Google Inc. 2013 copyright from the embedded name table | [SIL OFL 1.1](third_party/licenses/epaint_default_fonts-0.31.1/fonts/OFL.txt) |
| Ubuntu-Light.ttf | Canonical Ltd. 2011 copyright and Ubuntu Font Licence 1.0 from the embedded name table | [Ubuntu Font Licence](third_party/licenses/epaint_default_fonts-0.31.1/fonts/UFL.txt) |
| emoji-icon-font.ttf | John Slegers 2014; the font has no copyright/license name-table record | [Upstream MIT notice](third_party/licenses/epaint_default_fonts-0.31.1/fonts/emoji-icon-font-mit-license.txt) |
| Cantarell-Regular.ttf (sctk-adwaita 0.10.1) | Understanding Limited 2009–2011 and Jakub Steiner 2010–2011; embedded records and source specify OFL 1.1 | [OFL 1.1 text](third_party/upstream/sctk-adwaita/Cantarell-OFL-1.1.txt) and font records below |

Cantarell is a fallback font for Linux window title rendering. Its OFL text is
preserved from the pinned egui OFL copy; that text supplies no new copyright
holder. Cantarell's own copyright is preserved separately.
[third_party/fonts.json](third_party/fonts.json) contains the original SFNT name
records (copyright, trademark, manufacturer, designer, URLs and license fields),
with record identifiers, decoded text and raw bytes as hex, plus font hashes.
It also records three ttf-parser test fonts; these are inventory candidates, not
claimed application resources. The fonts themselves are not copied into the
release documentation. Upstream font conditions remain distinct from Rust code
licenses. The eframe default image and other resource candidates are recorded
conservatively even where the application supplies its own branded icon.

## Application icon — rights confirmation required

The project owner reports that the selected icon was generated during development
with ChatGPT and then selected by the owner. This is a provenance report, not an
ownership declaration. The source image is assets/icons/pdf-squeeze-icon.png;
scripts/generate_icons.py derives the platform icons from it. No grant of rights,
MIT classification, exclusivity claim or copyright holder is asserted here.
The owner must confirm the generation provenance, applicable service terms and
intended distribution rights before release. Existing branding is unchanged.

## Ghostscript — separate legal review required

Ghostscript remains an externally installed executable and is not included in
any application archive. Its AGPL/commercial licensing implications for this
application's integration and intended distribution remain unresolved. External
subprocess execution is not an automatic compatibility guarantee. Review the
actual integration and distribution model with appropriate authority and
[Artifex's licensing guidance](https://ghostscript.com/faq/) before release.
The crate inventory does not cover an end user's Ghostscript installation.

## Reproduction and maintenance

Use Rust/Cargo **1.89.0** (the native CI version) and Python **3.10 or later**.
No extra Python package or license-inventory service is needed.

1. Run `cargo +1.89.0 fetch --locked` to obtain every locked target's crate sources.
2. Set `RUSTUP_TOOLCHAIN=1.89.0` for the Python generator if that is not the default
   toolchain. Run `python3 scripts/license_inventory.py --check`. Metadata calls
   use `--locked --offline`; they do not update the resolution or fetch licenses.
3. To regenerate after a reviewed dependency change, run the generator without
   `--check`. Review the inventory diff, new notices, font records and issues.
   Generated material consists of THIRD_PARTY_NOTICES.md, inventory.json,
   fonts.json and third_party/licenses. Only that generated material is replaced;
   supplemental upstream inputs are preserved.
4. For an omitted upstream notice, identify the package's exact source revision,
   inspect its original license scope, retrieve the relevant original files,
   place them under third_party/upstream, and add immutable URLs, hashes and
   explicit package-version associations to supplemental.json. Record uncertainty
   instead of assigning another project's grant to it. The generator validates
   these local inputs; it never silently downloads a current branch's license.
5. Run `python3 scripts/verify_licenses.py` and
   `python3 -m unittest discover -s tests -p 'test_*.py'`.
6. Package with the existing script. Run
   `python3 scripts/verify_licenses.py --archive <archive>` for each archive.
   This checks every licensing file byte-for-byte against the checkout. Packaging
   refuses missing, empty or hash-mismatched notices and a changed lockfile.
7. `python3 scripts/verify_licenses.py --require-publishable` additionally requires
   a nonempty project LICENSE and zero recorded inventory issues. It currently
   fails intentionally. `license_inventory.py --check --require-complete` checks
   generated coverage independently. Neither flag is a legal approval mechanism.

All four native CI jobs regenerate and compare the inventory, run packaging tests
and verify archive notice bytes. The publication job retains the root LICENSE
guard, checks unresolved inventory issues, and rechecks documentation in all four
archives before checksums and publication. It cannot validate owner approval,
icon rights, Ghostscript obligations, or unrecorded third-party requirements.
Those remain human release-review responsibilities.
