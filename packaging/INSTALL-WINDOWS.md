# Windows x64 installation

1. Install 64-bit Ghostscript from the [official downloads page](https://ghostscript.com/releases/gsdnld.html). Make sure `gswin64c` is on `PATH`; `gswin64c --version` should work in a new terminal.
2. Extract this ZIP to a folder you control. Keep `pdf-squeeze.exe` and the documentation together.
3. Double-click `pdf-squeeze.exe` to open the desktop GUI. Restart it after installing Ghostscript.

The command-line form is `pdf-squeeze.exe input.pdf --output result.pdf`. Ghostscript is a separate installation and is not included in this archive.
