# Linux x64 installation

This binary is built on Ubuntu 22.04 x86_64. It is tested on that runner, not on every Linux distribution. A compatible glibc, X11 or Wayland desktop libraries, and a working desktop session are needed for the GUI. File dialogs use the XDG desktop portal when available, with Zenity as a fallback.

On Ubuntu 22.04, install Ghostscript and Zenity with `sudo apt install ghostscript zenity`. Check `gs --version`. Install any missing shared libraries reported by `ldd ./pdf-squeeze` from your distribution's packages.

Extract the archive with `tar -xzf pdf-squeeze-linux-x64.tar.gz`, then run `./pdf-squeeze` for the GUI or `./pdf-squeeze input.pdf --output result.pdf` for CLI use. Ghostscript is separately installed and is not included in this archive.

To add PDF Squeeze to your desktop application menu, run these commands from the extracted archive:

```sh
install -Dm755 pdf-squeeze "$HOME/.local/bin/pdf-squeeze"
install -Dm644 share/applications/pdf-squeeze.desktop "$HOME/.local/share/applications/pdf-squeeze.desktop"
mkdir -p "$HOME/.local/share/icons/hicolor"
cp -R share/icons/hicolor/. "$HOME/.local/share/icons/hicolor/"
```

Ensure `~/.local/bin` is on the graphical session's `PATH` so the launcher can find the executable. The desktop entry uses the packaged `pdf-squeeze` icon.
