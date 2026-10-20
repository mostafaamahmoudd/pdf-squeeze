# Compression notes

Each successful compression job runs Ghostscript exactly once, excluding installation/version checks. The default profile is `/ebook`; there is no resolution search or automatic fallback. `gs::CompressionProfile` centralizes the preset name so a future opt-in `/screen` profile can be added without restoring repeated conversions.

The engine validates input paths and preserves the existing output protections, then creates one candidate inside a temporary directory beside the destination. A conversion error or invalid candidate aborts the job. A candidate is checked even when it is larger than the original, so a failed conversion cannot become an unchanged-copy success.

Only a strictly smaller valid candidate is published. Otherwise, the original is copied once over the private candidate path, retaining the copied-byte-count check. A smaller candidate needs no additional full-file copy. `persist_noclobber` publishes the selected file without replacing an existing destination. Dropping temporary paths/directories cleans up on normal errors and completion.

Strict PDF error mode and known fatal stdout/stderr diagnostics guard conversion failures. Bounded candidate checks verify the PDF header, EOF/startxref trailer, offset bounds, and classic cross-reference-table marker. The existing PDF 1.4 output setting is retained. These checks are not a complete PDF parser or a guarantee of content preservation.

Both GUI and CLI call `compress::compress_pdf` and display its shared summary: original/output bytes, percentage saved, elapsed job time (including detection, validation and publication), profile, and compression invocation count. The GUI worker sends stage updates for detection, conversion, validation and saving; a spinner provides activity feedback without a time estimate or progress percentage.

Every Ghostscript invocation uses:

```text
-sDEVICE=pdfwrite
-dCompatibilityLevel=1.4
-dPDFSETTINGS=/ebook
-dDetectDuplicateImages=true
-dNOPAUSE -dQUIET -dBATCH
-dPDFSTOPONERROR=true
-sOutputFile=<temporary PDF>
<input PDF>
```

`/ebook` now supplies image resolution and downsampling thresholds as well as the general preset settings. The previous per-image DPI and threshold overrides are removed. Duplicate-image detection and all existing strict failure/diagnostic handling remain. Preset processing may change image quality and other document properties; the app makes no lossless, whole-document DPI, or target-size guarantee. A valid result may be larger than the input, particularly for already optimized or vector-heavy documents.
