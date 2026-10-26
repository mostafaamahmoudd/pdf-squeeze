# Release review

The guarded tag workflow publishes **Windows x64 and Linux x64 only**. macOS
binary publication is on hold; its packaging code and all unresolved evidence
remain preserved. See [platform publication](platform-publication.md) for the
exact dependency scope, selected license options, mandatory notices, Ghostscript
assessment and conditions requiring a new review.

A push to `ci/**`, `feat/**`, or `chore/**` or `workflow_dispatch` builds native
Windows/Linux archives without publishing. The Windows job reuses
`.github/workflows/windows-build.yml`, including PDF fixture and console checks.
Linux uses Ubuntu 22.04. Both run inventory regeneration, scoped license checks,
format, compilation, tests, real Ghostscript integration/GUI-worker tests, Clippy,
release builds, packaging tests, archive notice checks and extracted CLI tests.
Automated tests do not exercise an interactive GUI session; this limitation is
disclosed in the experimental release notes. Linux portability beyond compatible
Ubuntu 22.04 systems is not guaranteed; inspect `ldd` output and desktop setup.

## Publication procedure

1. Start from updated master on a feature branch. Update dependencies, license
   evidence or the policy only after reviewing the new distribution scope.
2. Use Rust/Cargo 1.89.0 and Python 3.10+. Run `cargo fetch --locked`, all checks in
   CONTRIBUTING.md, `python3 scripts/license_inventory.py --check`, and
   `python3 scripts/verify_licenses.py`. Run the Python regression suite.
3. Run `python3 scripts/verify_licenses.py --require-publishable --platform windows-x64`
   and the equivalent for `linux-x64`. These recompute exact default-feature
   normal/build trees, compare review input hashes and reject active gaps.
   Neither clears the 13 global records. Unscoped `--require-publishable` still
   fails intentionally. `--require-complete` is a global completeness check,
   not the approved-platform publication criterion.
4. Package on native runners. Verify each archive with the same scoped command
   plus `--archive <matching-archive>`. All notices, including inactive evidence,
   must still match the checkout. Review native CI and an independent code review
   before a one-line Conventional Commit `--no-ff` merge to master.
5. Push `v0.1.0` only at the reviewed master merge commit after the checks pass.
   Do not create a Release manually or upload local substitute binaries.
6. The tag workflow rebuilds both native packages and checks the version against
   Cargo metadata, nonempty project LICENSE, both scoped policies and ancestry
   on fetched master. It downloads exactly two archives, verifies notices,
   generates and checks SHA256SUMS.txt, creates a draft with exactly three assets,
   and publishes it only after all required jobs succeed. It refuses to overwrite
   an existing Release.
7. Download all three assets from the public Release, run `sha256sum -c SHA256SUMS.txt`,
   verify archive notices against the tagged checkout, and inspect the exact
   public asset list and GitHub digests. Report the actual public URL and hashes.

No Ghostscript executable, DLL, installer or resource is included. Users install
it separately under its own terms. Its ordinary CLI/PDF-file boundary supports
the reviewed separate-program assessment; bundling, linking, modification,
private protocols or network-service use requires reassessment. A formal legal
letter is not an automatic precondition. A substantiated unmet distribution
obligation remains a blocker for the affected platform.
