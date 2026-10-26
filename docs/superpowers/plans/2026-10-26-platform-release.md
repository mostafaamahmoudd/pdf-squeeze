# Windows and Linux v0.1.0 publication plan

**Goal:** Publish verifiable Windows x64 and Linux x64 binaries through the existing guarded tag workflow, preserving all macOS evidence.

**Design:** Keep the complete inventory and strict global publication mode. Add an explicitly requested platform mode bound to the reviewed lockfile, manifest, inventory, integration source, and exact default-feature normal/build dependency trees. Only Windows x64 and Linux x64 are approved. No issue is deleted or waived for an active package. Keep all notices in both archives. Publish exactly those two archives and their checksums.

**Approaches:** Clearing the global inventory would erase unresolved evidence; a broad issue allowlist could hide a newly active obligation. A pinned platform policy with freshly recomputed trees supports this release while failing on drift. This implements the user's requested platform-scoped policy and authorized execution, PR, merge, and publication sequence.

**Tech stack:** Rust/Cargo 1.89.0, Python standard library, GitHub Actions and gh.

## Constraints and review focus

- Preserve all 13 unresolved records, original notice bytes, and the macOS publication hold.
- Keep the project LICENSE, pointer validation, lockfile checks, native smoke tests, checksums, and master ancestry guard.
- Reject changed dependencies/features, active issues, unreviewed grants, stale evidence, missing notices, and unsupported platforms.
- Assess actual Ghostscript communication and authoritative terms; no automatic lawyer-letter requirement.
- Follow one-line Conventional Commits and a --no-ff merge. No attribution trailers or force pushes.

## Tasks

- [x] Record exact trees, selected license options, mandatory notices, Ghostscript assessment, and runtime license evidence.
- [x] Add regression tests for scoped success, active issues/pointers, dependency drift, unsupported platforms, changed inputs, archive mismatch, and preserved global rejection; watch failures before implementation.
- [x] Implement the minimal scoped verifier and pinned policy; run the complete Python suite and inventory verification.
- [x] Scope the guarded workflow's build/publication assets to Windows/Linux; retain build/test/archive safeguards and update release documentation.
- [ ] Run local fmt/check/test/ignored tests/clippy/release build, notice/archive checks and CLI smoke test; open a feature PR and run native CI.
- [ ] Obtain independent code review, resolve material findings, and merge with --no-ff after CI passes.
- [ ] Tag the verified master commit v0.1.0, wait for guarded publication, download public assets, and verify exact assets, notices, and checksums.

## Execution record

- Updated origin/master is 252333ebeb187a8662d14c98f087210b96d9f345. Feature branch: feat/windows-linux-v0.1.0. Work proceeds in the clean existing checkout on that branch.
- Baseline: 36 Python tests passed; Rust format/check/test/ignored tests/clippy/release build passed on Rust 1.89.0; local Ghostscript 9.55.0.
- Exact trees: Windows 144 packages, Linux 269, macOS 154 each; Windows/Linux union 290. No unresolved record active in Windows/Linux; nine active on each macOS target.

- Independent review identified two P1 Windows verification problems: host-conditioned build dependencies and checkout line endings. Fixed with distinct pinned Linux/native-Windows inspection trees, a native obligations superset (146 Windows packages, 269 Linux; union 292), and LF attributes for every newly hashed text input. The cross-host build-dependency regression failed before the fix and now passes; Windows checkout filters preserve pinned bytes. Native Windows CI must confirm the exact snapshot.
- Final local checks: 47 Python tests pass; unchanged Rust implementation passed fmt/check/test/ignored tests/clippy/release build; both scoped license checks pass; complete inventory regeneration passes with 429 crates and 13 unresolved records retained. Global strict and both macOS scoped checks reject as intended. Linux archive, licensing bytes, dynamic libraries, desktop launcher and extracted CLI smoke test pass.
