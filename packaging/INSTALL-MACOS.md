# macOS installation

Choose the ARM64 archive for Apple Silicon or the x64 archive for an Intel Mac. Unzip it and move `PDF Squeeze.app` to Applications or another folder. Install Ghostscript separately with `brew install ghostscript`; `gs --version` should work in a new terminal. Restart PDF Squeeze after installation.

These experimental bundles are **not Developer ID signed or notarized**. Gatekeeper may block a downloaded bundle. If you trust the archive after checking its SHA-256 checksum, first try to open the app, then use macOS **System Settings → Privacy & Security → Open Anyway** for this app if the option is offered. Do not disable system-wide security protections. A polished public release needs Developer ID signing and Apple notarization.

The CLI executable is inside `PDF Squeeze.app/Contents/MacOS/pdf-squeeze`. Ghostscript is not included in the bundle or archive.
