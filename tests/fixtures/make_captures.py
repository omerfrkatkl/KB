"""Fixture builders for the ingest tests.

**These are not captures and must never be read as evidence about extraction.**
They are geometric and structural fixtures: a PDF with known page count and known
text, a PNG of known size, a JPEG carrying synthetic EXIF camera tags. They exist
to exercise the plumbing — routing, hashing, grouping, the resolution gate's
arithmetic — none of which has anything to do with what a model can read off a
photograph of a board.

`docs/SLICE-FINDINGS.md` records what it cost the last time generated material
was mistaken for real material. The rule that follows from it: a fixture may test
code, never fidelity.
"""

from __future__ import annotations

import struct
from pathlib import Path

import cv2
import fitz
import numpy as np


def make_pdf(path: Path, pages: int = 3, text: str = "Definition. A domain is") -> Path:
    doc = fitz.open()
    for i in range(pages):
        page = doc.new_page(width=595, height=842)     # A4 at 72 dpi
        page.insert_text((72, 100), f"{text} page {i + 1}.", fontsize=11)
    doc.save(path)
    doc.close()
    return path


def make_page_image(path: Path, text_height_px: int = 30, width: int = 1200,
                    height: int = 900) -> Path:
    """A white page with black bars of a known height, as glyph stand-ins.

    The resolution gate measures connected-component heights, so a field of bars
    of height h must measure h. That is the arithmetic being tested — nothing
    here claims to look like text.
    """
    img = np.full((height, width), 255, np.uint8)
    y = 60
    while y + text_height_px < height - 60:
        for x in range(80, width - 80, 40):
            img[y:y + text_height_px, x:x + max(3, text_height_px // 3)] = 0
        y += text_height_px * 2
    cv2.imwrite(str(path), img)
    return path


def make_photo(path: Path, make: str = "TestCam", model: str = "TC-1",
               taken: str = "2026:05:03 14:21:07", size: tuple[int, int] = (1200, 900)) -> Path:
    """A JPEG carrying real EXIF Make/Model/DateTimeOriginal in an APP1 segment.

    Written by hand rather than by a library: the dependency list is closed, and
    the reader under test parses the same bytes a phone would write.
    """
    img = np.full((size[1], size[0]), 200, np.uint8)
    img[100:130, 100:600] = 20
    ok, buf = cv2.imencode(".jpg", img)
    assert ok
    jpeg = bytes(buf)
    app1 = _exif_app1(make, model, taken)
    # Insert APP1 straight after SOI, which is where a camera puts it.
    path.write_bytes(jpeg[:2] + app1 + jpeg[2:])
    return path


def _exif_app1(make: str, model: str, taken: str) -> bytes:
    """Little-endian TIFF: IFD0 with Make/Model/ExifIFDPointer, Exif IFD with
    DateTimeOriginal. Offsets are computed, not guessed."""
    def asciiz(s: str) -> bytes:
        return s.encode("ascii") + b"\x00"

    make_b, model_b, taken_b = asciiz(make), asciiz(model), asciiz(taken)

    header = b"II*\x00" + struct.pack("<I", 8)
    ifd0_entries = 3
    ifd0_size = 2 + ifd0_entries * 12 + 4
    exif_ifd_at = 8 + ifd0_size
    exif_entries = 1
    exif_size = 2 + exif_entries * 12 + 4
    data_at = exif_ifd_at + exif_size

    make_at = data_at
    model_at = make_at + len(make_b)
    taken_at = model_at + len(model_b)

    ifd0 = struct.pack("<H", ifd0_entries)
    ifd0 += struct.pack("<HHII", 0x010F, 2, len(make_b), make_at)
    ifd0 += struct.pack("<HHII", 0x0110, 2, len(model_b), model_at)
    ifd0 += struct.pack("<HHII", 0x8769, 4, 1, exif_ifd_at)
    ifd0 += struct.pack("<I", 0)

    exif_ifd = struct.pack("<H", exif_entries)
    exif_ifd += struct.pack("<HHII", 0x9003, 2, len(taken_b), taken_at)
    exif_ifd += struct.pack("<I", 0)

    tiff = header + ifd0 + exif_ifd + make_b + model_b + taken_b
    payload = b"Exif\x00\x00" + tiff
    return b"\xff\xe1" + struct.pack(">H", len(payload) + 2) + payload


def make_screenshot(path: Path, **kw) -> Path:
    """A PNG with no EXIF at all — what a screenshot tool produces."""
    return make_page_image(path, **kw)
