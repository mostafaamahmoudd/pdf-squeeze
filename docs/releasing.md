# Release review

The release workflow builds four native archives on GitHub-hosted runners. A push to a `ci/**`, `feat/**`, or `chore/**` branch runs a test build and uploads archives without publishing a Release. `workflow_dispatch` also runs a test build. A pushed `v<package-version>` tag starts the same required jobs; the publishing job runs only after all four succeed, checks the tag against Cargo metadata, verifies the tag commit is on `master`, creates checksums and notes, and publishes a new Release. It refuses to overwrite an existing Release.

The Windows job reuses `.github/workflows/windows-build.yml`, including the PDF fixture and console-suppression tests. Linux uses Ubuntu 22.04, and the two macOS jobs run on native Apple Silicon and Intel runners. The archive checks exercise the extracted CLI, not the interactive GUI. Native GUI smoke tests remain a separate release review item.

## Runtime and distribution checks

- Linux: inspect the release job's `ldd` output and test on the intended distributions. The Ubuntu 22.04 build is not universally portable. A graphical X11 or Wayland session, an XDG desktop portal backend, and Zenity are needed for a dependable GUI and file picker.
- macOS: the `.app` archives are valid experimental bundles, but they have no Developer ID signature or Apple notarization. Gatekeeper can block a downloaded bundle. A polished public release requires Developer ID signing, notarization, and validation on actual Macs.
- Ghostscript: users install it separately; no archive includes it. Verify the intended distribution and use against [Artifex's licensing guidance](https://ghostscript.com/faq/). External-process use is not an automatic AGPL exemption.
- Licensing: see [LICENSING.md](../LICENSING.md) for the owner-approved source license and icon distribution statement, third-party inventory gaps, font notices and Ghostscript review. The publishing job retains the nonempty root `LICENSE` guard and also requires current third-party documentation without unresolved inventory issues. Every archive is checked against the committed notice bytes. These checks do not constitute legal clearance.

Do not push a version tag until the native builds, license review, interactive GUI checks, and release notes have been reviewed. The workflow does not sign or notarize macOS bundles. The current decision list is in [release readiness](release-readiness.md).

## Reproducing licensing checks

Use Rust 1.89.0 and Python 3.10 or later. Run `cargo fetch --locked`, then
`python3 scripts/license_inventory.py --check` and `python3 scripts/verify_licenses.py`.
See [LICENSING.md](../LICENSING.md) before regenerating or editing inventory inputs.
Run `python3 -m unittest discover -s tests -p 'test_*.py'` for inventory, archive,
permission and publication-gate regression tests. After packaging, run
`python3 scripts/verify_licenses.py --archive <archive>` for each platform.
The publication-specific `--require-publishable` mode currently fails intentionally
because 13 upstream inventory gaps remain unresolved. The owner-approved root
`LICENSE` is present.
