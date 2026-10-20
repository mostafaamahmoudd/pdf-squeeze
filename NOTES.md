# Compression notes

The target-size search was removed because the tool now optimizes for a small output at acceptable quality, rather than a user-specified size budget. The 72 DPI floor aims to keep text in raster content readable; below that, many pages become unusable. Vector text is not controlled by image DPI.

`find_best_dpi` measures 72 and 300 DPI, then halves the interval while its bounds differ by more than 5 DPI. It compares each midpoint with the current lower-bound sample to choose a half, and retains the smallest output measured at any step. Its size-producing closure keeps the decision logic testable without PDFs or Ghostscript. Ghostscript output size can be non-monotonic, so this heuristic does not prove a global minimum.

After the search, the tool compares the smallest Ghostscript output with the original input. It saves the Ghostscript result only when that result is strictly smaller. Otherwise, it copies the original unchanged: some PDFs are already optimized, and Ghostscript can enlarge them. Both outcomes provide a usable output file.

Each attempt is written inside a temporary directory in the output folder. The selected PDF or unchanged input copy is moved to the requested path only after the search finishes, and only if that path does not already exist. Dropping the temporary directory removes all other attempts, including after an error. The tool compares file sizes with `metadata().len()` and does not parse PDF content; it checks only the `%PDF-` header before starting Ghostscript. The GUI receives a progress update after each Ghostscript invocation. Its progress bar uses an eight-step estimate, so one step may take a while on a large file.

Every Ghostscript invocation uses:

```text
-sDEVICE=pdfwrite
-dCompatibilityLevel=1.4
-dPDFSETTINGS=/ebook
-dColorImageResolution=<dpi>
-dGrayImageResolution=<dpi>
-dMonoImageResolution=<dpi>
-dColorImageDownsampleThreshold=1.0
-dGrayImageDownsampleThreshold=1.0
-dMonoImageDownsampleThreshold=1.0
-dDetectDuplicateImages=true
-dNOPAUSE -dQUIET -dBATCH
-sOutputFile=<temporary PDF>
<input PDF>
```

`/ebook` supplies Ghostscript's general PDF compression settings. The explicit image resolution flags set the quality level being searched. The `DownsampleThreshold=1.0` flags make eligible images downsample at the chosen resolution rather than waiting for a higher threshold. Duplicate-image detection can avoid storing repeated images more than once. Quiet batch mode prevents interactive prompts; subprocess stderr is retained for errors.
