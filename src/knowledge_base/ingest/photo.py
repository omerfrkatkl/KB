"""The photo chain (§I-6.3a) — a photographed board becomes rectified crops.

    EXIF orientation -> quad detection -> perspective warp -> CLAHE

Quad detection: grayscale, bilateral filter, adaptive threshold and Canny,
contour extraction, convex quad approximation, area and aspect filters, **keep
full quads and discard edge-clipped ones**.

Two behaviours are load-bearing and both are about not losing content:

* **Edge-clipped quads are discarded, not cropped.** A board running off the
  frame would otherwise yield a crop that looks complete and is not — the
  extractor would read it confidently and be wrong with nothing to detect it.
  The prompt always carries the ignore-edge-clipped-content instruction as the
  second line of defence.
* **No confident quad falls back to the whole image**, with a flag. A photo that
  produced no crop is still material; refusing it would silently drop a lecture.

Geometry cannot catch a *fully visible* board belonging to a different course —
that was observed in real material, where a differential-geometry board shared
the frame with a ring-theory lecture. Only the topical test can, which is why the
extractor is given its field and lexicon and the `foreign-subject` exclusion
class exists.

**This module's tests use generated geometric fixtures.** They prove the warp and
the filters do what they say; they are not evidence about board-photo extraction
fidelity. That is B11 and needs the owner's real photographs (WP0.3).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import cv2
import numpy as np

from knowledge_base.ingest import exif
from knowledge_base.ops.log import get

log = get("photo")

MIN_AREA_FRACTION = 0.04     # a board smaller than this is furniture, not content
MAX_AREA_FRACTION = 0.995    # above this the "quad" is the frame itself
MIN_ASPECT, MAX_ASPECT = 0.25, 6.0
EDGE_MARGIN_PX = 3           # nearer than this to the border counts as clipped
CLAHE_CLIP, CLAHE_GRID = 2.0, (8, 8)


@dataclass
class BoardCrop:
    index: int
    path: Path
    quad: list[list[int]]
    area_fraction: float


@dataclass
class PhotoResult:
    source: Path
    crops: list[BoardCrop] = field(default_factory=list)
    fell_back: bool = False           # no confident quad; whole image used
    discarded_clipped: int = 0

    @property
    def flagged(self) -> bool:
        return self.fell_back


def apply_orientation(image: "np.ndarray", orientation: int) -> "np.ndarray":
    """EXIF orientation, applied before anything measures the geometry."""
    if orientation == 3:
        return cv2.rotate(image, cv2.ROTATE_180)
    if orientation == 6:
        return cv2.rotate(image, cv2.ROTATE_90_CLOCKWISE)
    if orientation == 8:
        return cv2.rotate(image, cv2.ROTATE_90_COUNTERCLOCKWISE)
    return image


def detect_quads(image: "np.ndarray") -> tuple[list["np.ndarray"], int]:
    """Return (kept quads, number discarded for touching the frame edge)."""
    height, width = image.shape[:2]
    total = float(height * width)

    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if image.ndim == 3 else image
    smoothed = cv2.bilateralFilter(gray, 9, 75, 75)
    threshold = cv2.adaptiveThreshold(smoothed, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                      cv2.THRESH_BINARY, 15, 4)
    edges = cv2.Canny(smoothed, 50, 150)
    combined = cv2.bitwise_or(edges, cv2.bitwise_not(threshold))
    combined = cv2.morphologyEx(combined, cv2.MORPH_CLOSE, np.ones((5, 5), np.uint8))

    contours, _ = cv2.findContours(combined, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    kept: list[np.ndarray] = []
    clipped = 0
    for contour in contours:
        # The screen runs on the bounding rectangle, not on the polygon. A board
        # running off the frame often approximates to five or six points, or to
        # a self-intersecting outline whose contourArea is near zero — screening
        # on that would report no clipped regions for a photograph full of them,
        # which is a diagnostic that lies in exactly the case it exists for.
        bx, by, bw, bh = cv2.boundingRect(contour)
        if bw * bh < MIN_AREA_FRACTION * total:
            continue
        if (bx <= EDGE_MARGIN_PX or by <= EDGE_MARGIN_PX
                or bx + bw >= width - EDGE_MARGIN_PX
                or by + bh >= height - EDGE_MARGIN_PX):
            clipped += 1
            continue

        approx = cv2.approxPolyDP(contour, 0.02 * cv2.arcLength(contour, True), True)
        if len(approx) != 4 or not cv2.isContourConvex(approx):
            continue
        area = cv2.contourArea(approx)
        if not (MIN_AREA_FRACTION * total <= area <= MAX_AREA_FRACTION * total):
            continue
        points = approx.reshape(4, 2)
        w, h = _extent(points)
        if h == 0 or not (MIN_ASPECT <= w / h <= MAX_ASPECT):
            continue
        kept.append(_order(points))
    return _drop_nested(kept), clipped


def _extent(points) -> tuple[float, float]:
    xs, ys = points[:, 0], points[:, 1]
    return float(xs.max() - xs.min()), float(ys.max() - ys.min())


def _touches_edge(points, width: int, height: int) -> bool:
    xs, ys = points[:, 0], points[:, 1]
    return bool(xs.min() <= EDGE_MARGIN_PX or ys.min() <= EDGE_MARGIN_PX
                or xs.max() >= width - 1 - EDGE_MARGIN_PX
                or ys.max() >= height - 1 - EDGE_MARGIN_PX)


def _order(points) -> "np.ndarray":
    """Corners as top-left, top-right, bottom-right, bottom-left."""
    points = points.astype(np.float32)
    total = points.sum(axis=1)
    diff = np.diff(points, axis=1).ravel()
    return np.array([points[np.argmin(total)], points[np.argmin(diff)],
                     points[np.argmax(total)], points[np.argmax(diff)]], np.float32)


def _drop_nested(quads: list["np.ndarray"]) -> list["np.ndarray"]:
    """Keep the outermost of any nested pair — a board's frame and its writing
    area both detect, and the inner one loses the edges of the content."""
    out: list[np.ndarray] = []
    for quad in sorted(quads, key=lambda q: -cv2.contourArea(q)):
        centre = quad.mean(axis=0)
        if any(cv2.pointPolygonTest(kept.astype(np.float32), tuple(centre), False) >= 0
               for kept in out):
            continue
        out.append(quad)
    return out


def warp(image: "np.ndarray", quad: "np.ndarray") -> "np.ndarray":
    (tl, tr, br, bl) = quad
    width = int(max(np.linalg.norm(br - bl), np.linalg.norm(tr - tl)))
    height = int(max(np.linalg.norm(tr - br), np.linalg.norm(tl - bl)))
    width, height = max(width, 1), max(height, 1)
    target = np.array([[0, 0], [width - 1, 0], [width - 1, height - 1],
                       [0, height - 1]], np.float32)
    return cv2.warpPerspective(image, cv2.getPerspectiveTransform(quad, target),
                               (width, height))


def enhance(image: "np.ndarray") -> "np.ndarray":
    """CLAHE on the luminance channel — chalk on a dark board is low contrast
    unevenly, which is exactly what a local histogram equalisation is for."""
    clahe = cv2.createCLAHE(clipLimit=CLAHE_CLIP, tileGridSize=CLAHE_GRID)
    if image.ndim == 2:
        return clahe.apply(image)
    lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
    lab[:, :, 0] = clahe.apply(lab[:, :, 0])
    return cv2.cvtColor(lab, cv2.COLOR_LAB2BGR)


def process(path: Path, out_dir: Path) -> PhotoResult:
    """The whole chain. Originals are never written to; crops go to `derived/`."""
    image = cv2.imread(str(path), cv2.IMREAD_COLOR)
    if image is None:
        raise ValueError(f"unreadable photograph: {path}")
    image = apply_orientation(image, exif.orientation(path))
    out_dir.mkdir(parents=True, exist_ok=True)

    quads, clipped = detect_quads(image)
    result = PhotoResult(source=path, discarded_clipped=clipped)
    total = float(image.shape[0] * image.shape[1])

    if not quads:
        log.info("%s: no confident quad — using the whole image and flagging it",
                 path.name)
        dest = out_dir / f"{path.stem}-full.png"
        cv2.imwrite(str(dest), enhance(image))
        result.crops.append(BoardCrop(index=0, path=dest,
                                      quad=[[0, 0]], area_fraction=1.0))
        result.fell_back = True
        return result

    for index, quad in enumerate(quads, 1):
        dest = out_dir / f"{path.stem}-b{index}.png"
        cv2.imwrite(str(dest), enhance(warp(image, quad)))
        result.crops.append(BoardCrop(
            index=index, path=dest, quad=quad.astype(int).tolist(),
            area_fraction=float(cv2.contourArea(quad) / total)))
    return result
