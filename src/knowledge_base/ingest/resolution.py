"""The resolution gate (§I-6.3c) — the one preprocessing step raster also gets.

It guards the failure mode that hides best: a capture where a subscript, a prime,
or an integral bound is simply not present in the pixels. Nothing downstream can
detect that. The extractor will read the expression, transcribe it confidently,
and be wrong in a way no validator can see, because the output is well-formed.

Measurement: binarise, take connected components, and treat the median height of
the text-like components as the capture's text height. Components that are
obviously not glyphs (rules, whole-image blobs, single pixels) are excluded
before the median is taken, since a full-width chalk line would otherwise drag it
around.

The threshold itself is **measured, not chosen** — `resolution_floor_px` comes
from WP0.3 over the owner's real captures (B16). Until it is measured the gate
reports the height and passes everything: a guessed floor would silently reject
good captures, and the plan is explicit that this number comes from material.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np

from knowledge_base.ops.log import get

log = get("resolution")


@dataclass(frozen=True)
class Measurement:
    text_height_px: float
    component_count: int
    passes: bool
    floor_px: int
    measured: bool     # False => the floor is unset; nothing was rejected


def measure(path: Path | str) -> tuple[float, int]:
    """Median text height in pixels, and how many components it came from."""
    img = cv2.imread(str(path), cv2.IMREAD_GRAYSCALE)
    if img is None:
        raise ValueError(f"unreadable image: {path}")
    return measure_array(img)


def measure_array(gray: "np.ndarray") -> tuple[float, int]:
    h, w = gray.shape[:2]
    # Otsu on a blurred copy: robust to the uneven lighting of a photographed
    # board and to the anti-aliasing of a screenshot alike.
    blurred = cv2.GaussianBlur(gray, (3, 3), 0)
    _, binary = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    count, _, stats, _ = cv2.connectedComponentsWithStats(binary, connectivity=8)

    heights = []
    for i in range(1, count):
        x, y, cw, ch, area = stats[i]
        if ch < 3 or area < 6:
            continue                      # speckle
        if ch > h * 0.5 or cw > w * 0.9:
            continue                      # rules, borders, whole-image blobs
        if cw > 0 and ch / cw > 25:
            continue                      # a vertical line, not a glyph
        heights.append(float(ch))

    if not heights:
        return 0.0, 0
    return float(np.median(heights)), len(heights)


def gate(path: Path | str, floor_px: int) -> Measurement:
    height, n = measure(path)
    measured = floor_px > 0
    passes = True if not measured else height >= floor_px
    if measured and not passes:
        log.warning("%s: median text height %.1fpx is below the measured floor of %dpx "
                    "— routing to review rather than extraction", path, height, floor_px)
    elif not measured:
        log.debug("%s: text height %.1fpx (floor unmeasured — B16, WP0.3)", path, height)
    return Measurement(text_height_px=height, component_count=n, passes=passes,
                       floor_px=floor_px, measured=measured)
