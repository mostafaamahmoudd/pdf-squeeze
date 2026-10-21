"""Regenerate branded icons from the checked-in source PNG (requires Pillow)."""

import io
import struct
from pathlib import Path

from PIL import Image


ROOT = Path(__file__).resolve().parent.parent / "assets" / "icons"
SOURCE = ROOT / "pdf-squeeze-icon.png"
LINUX_SIZES = (16, 32, 48, 64, 128, 256, 512)
MAC_SIZES = (
    (b"icp4", 16), (b"icp5", 32), (b"icp6", 64),
    (b"ic07", 128), (b"ic08", 256), (b"ic09", 512), (b"ic10", 1024),
    (b"ic11", 32), (b"ic12", 64), (b"ic13", 256), (b"ic14", 512),
)


def main() -> None:
    with Image.open(SOURCE) as opened:
        if opened.width != opened.height or opened.width < 1024:
            raise ValueError("Source icon must be square and at least 1024 pixels wide")
        source = opened.convert("RGBA")

        def resized(size: int) -> Image.Image:
            return source.resize((size, size), Image.Resampling.LANCZOS)

        for size in LINUX_SIZES:
            destination = ROOT / "hicolor" / f"{size}x{size}" / "apps" / "pdf-squeeze.png"
            destination.parent.mkdir(parents=True, exist_ok=True)
            resized(size).save(destination, optimize=True)

        resized(256).save(
            ROOT / "pdf-squeeze.ico", format="ICO",
            sizes=[(size, size) for size in (16, 24, 32, 48, 64, 128, 256)],
        )

        chunks = []
        for kind, size in MAC_SIZES:
            image_data = io.BytesIO()
            resized(size).save(image_data, format="PNG")
            data = image_data.getvalue()
            chunks.append(kind + struct.pack(">I", len(data) + 8) + data)
        (ROOT / "pdf-squeeze.icns").write_bytes(
            b"icns" + struct.pack(">I", 8 + sum(map(len, chunks))) + b"".join(chunks)
        )


if __name__ == "__main__":
    main()
