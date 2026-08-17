"""A minimal, dependency-free EXIF reader.

Four fields decide real behaviour and nothing else here matters:

* `Make` / `Model` — presence of camera tags is what separates a **photo** from a
  **raster** capture (§I-6.3). Get this wrong and a screenshot goes through
  board-quad detection, which can lock onto a figure box and crop content away.
* `DateTimeOriginal` — signal 2 of the session-identity precedence (§I-6.5).
* `Orientation` — applied before quad detection in the photo chain.

**Why no library.** The dependency list is closed (§I-1) and none of `pymupdf`,
`opencv-python-headless`, or the rest reads EXIF. Rather than add one for four
tags, this parses the TIFF block directly. The parse is container-agnostic: it
locates the `Exif\\x00\\x00` marker, which is how the block is introduced inside a
JPEG APP1 segment, a HEIF `Exif` item, and a PNG `eXIf` chunk alike, and falls
back to a bare TIFF header for `.tif` files. A file whose EXIF cannot be read
yields `{}` and is treated as carrying no camera tags — the conservative
direction, since a raster is passed through untouched (§I-6.3b) while a
misidentified photo would be geometrically transformed.
"""

from __future__ import annotations

import struct
from datetime import datetime
from pathlib import Path

# Tag ids we read. The rest of the block is dumped as raw ids so the registry
# keeps the full record without this module having to know every vendor tag.
TAGS = {
    0x010F: "Make",
    0x0110: "Model",
    0x0112: "Orientation",
    0x0132: "DateTime",
    0x8769: "ExifIFDPointer",
}
EXIF_TAGS = {
    0x9003: "DateTimeOriginal",
    0x9004: "DateTimeDigitized",
    0xA002: "PixelXDimension",
    0xA003: "PixelYDimension",
}

_TYPE_SIZE = {1: 1, 2: 1, 3: 2, 4: 4, 5: 8, 6: 1, 7: 1, 8: 2, 9: 4, 10: 8, 11: 4, 12: 8}
_MARKER = b"Exif\x00\x00"
_MAX_SCAN = 1 << 20  # EXIF lives near the start of every container we handle


def read(path: Path | str) -> dict[str, object]:
    """Return the decoded tags, or `{}` when the file carries none we can read."""
    try:
        head = Path(path).open("rb").read(_MAX_SCAN)
    except OSError:
        return {}
    tiff = _locate_tiff(head)
    if tiff is None:
        return {}
    block, offset = tiff
    try:
        return _parse_tiff(block, offset)
    except (struct.error, IndexError, ValueError, UnicodeDecodeError):
        return {}


def camera_tags(path: Path | str) -> bool:
    """True iff the file carries Make/Model — the §I-6.3 photo-vs-raster test."""
    tags = read(path)
    return bool(tags.get("Make") or tags.get("Model"))


def datetime_original(path: Path | str) -> datetime | None:
    tags = read(path)
    for key in ("DateTimeOriginal", "DateTimeDigitized", "DateTime"):
        parsed = _parse_exif_datetime(tags.get(key))
        if parsed:
            return parsed
    return None


def orientation(path: Path | str) -> int:
    try:
        return int(read(path).get("Orientation", 1) or 1)
    except (TypeError, ValueError):
        return 1


# ── internals ─────────────────────────────────────────────────────────

def _locate_tiff(data: bytes) -> tuple[bytes, int] | None:
    i = data.find(_MARKER)
    if i >= 0:
        return data, i + len(_MARKER)
    if data[:4] in (b"II*\x00", b"MM\x00*"):
        return data, 0
    return None


def _parse_tiff(data: bytes, base: int) -> dict[str, object]:
    endian = data[base:base + 2]
    if endian == b"II":
        e = "<"
    elif endian == b"MM":
        e = ">"
    else:
        return {}
    magic, first = struct.unpack_from(e + "HI", data, base + 2)
    if magic != 42:
        return {}

    out: dict[str, object] = {}
    _read_ifd(data, base, base + first, e, TAGS, out)
    ptr = out.pop("ExifIFDPointer", None)
    if isinstance(ptr, int):
        _read_ifd(data, base, base + ptr, e, EXIF_TAGS, out)
    return out


def _read_ifd(data, base, offset, e, names, out) -> None:
    if offset + 2 > len(data):
        return
    (count,) = struct.unpack_from(e + "H", data, offset)
    for i in range(count):
        entry = offset + 2 + i * 12
        if entry + 12 > len(data):
            return
        tag, typ, n = struct.unpack_from(e + "HHI", data, entry)
        if tag not in names:
            continue
        size = _TYPE_SIZE.get(typ, 0) * n
        if size == 0:
            continue
        if size <= 4:
            payload = data[entry + 8:entry + 8 + size]
        else:
            (at,) = struct.unpack_from(e + "I", data, entry + 8)
            payload = data[base + at:base + at + size]
            if len(payload) < size:
                continue
        out[names[tag]] = _decode(payload, typ, n, e)


def _decode(payload: bytes, typ: int, n: int, e: str):
    if typ == 2:  # ASCII
        return payload.split(b"\x00", 1)[0].decode("utf-8", "replace").strip()
    if typ == 3:
        vals = struct.unpack_from(e + f"{n}H", payload)
    elif typ == 4:
        vals = struct.unpack_from(e + f"{n}I", payload)
    elif typ == 9:
        vals = struct.unpack_from(e + f"{n}i", payload)
    else:
        return payload
    return vals[0] if n == 1 else list(vals)


def _parse_exif_datetime(raw) -> datetime | None:
    if not isinstance(raw, str):
        return None
    for fmt in ("%Y:%m:%d %H:%M:%S", "%Y-%m-%d %H:%M:%S"):
        try:
            return datetime.strptime(raw.strip(), fmt)
        except ValueError:
            continue
    return None
