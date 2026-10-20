# Compression notes

`find_best_dpi` preserves the original if it already fits. Otherwise, it measures the 50 DPI result first. If it is above the target, that is the selected fallback. Otherwise, it measures 300 DPI. If 300 DPI fits, it wins. Between those bounds, binary search keeps the largest measured DPI that fits and stops when the bounds differ by at most 5 DPI. The decision function accepts a size-producing closure, so unit tests need no PDFs or Ghostscript. Ghostscript output size can vary non-monotonically with DPI, so the search is an approximation to the highest fitting quality.

Each attempt is written inside a temporary directory in the output folder. The selected PDF is moved to the requested path only after the search finishes, and only if that path does not already exist. Dropping the temporary directory removes all other attempts, including after an error. The tool compares file sizes with `metadata().len()` and does not parse PDF content; it checks only the `%PDF-` header before starting Ghostscript.

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
