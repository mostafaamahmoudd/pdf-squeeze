# Release review

The release workflow builds four native archives on GitHub-hosted runners. A push to a `ci/**` branch runs a test build and uploads archives without publishing a Release. Once this workflow is merged into the default branch, `workflow_dispatch` also runs a test build. A pushed `v<package-version>` tag starts the same required jobs; the publishing job runs only after all four succeed, checks the tag against Cargo metadata, verifies the tag commit is on `master`, creates checksums and notes, and publishes a new Release. It refuses to overwrite an existing Release.

The Windows job reuses `.github/workflows/windows-build.yml`, including the PDF fixture and console-suppression tests. Linux uses Ubuntu 22.04, and the two macOS jobs run on native Apple Silicon and Intel runners. The archive checks exercise the extracted CLI, not the interactive GUI. Native GUI smoke tests remain a separate release review item.

## Runtime and distribution checks

- Linux: inspect the release job's `ldd` output and test on the intended distributions. The Ubuntu 22.04 build is not universally portable. A graphical X11 or Wayland session, an XDG desktop portal backend, and Zenity are needed for a dependable GUI and file picker.
- macOS: the `.app` archives are valid experimental bundles, but they have no Developer ID signature or Apple notarization. Gatekeeper can block a downloaded bundle. A polished public release requires Developer ID signing, notarization, and validation on actual Macs.
- Ghostscript: users install it separately; no archive includes it. Verify the intended distribution and use against [Artifex's licensing guidance](https://ghostscript.com/faq/). External-process use is not an automatic AGPL exemption.
- Project license: `Cargo.toml` declares MIT, but this repository currently has no verified `LICENSE` text. Confirm copyright ownership and add the correct license file and any required third-party notices before a public release.

Do not push a version tag until the native builds, license review, interactive GUI checks, and release notes have been reviewed. The workflow does not sign or notarize macOS bundles.
