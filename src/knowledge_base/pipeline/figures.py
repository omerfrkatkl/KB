"""Figures (§I-11, WP3.3) — bbox to asset, behind a review gate.

Two sources, one preference:

* a **PDF's embedded image** is used when one overlaps the bbox, because the
  publisher's own raster beats a crop of a 300 dpi re-render of it;
* otherwise the region is **cropped from the capture** with padding.

Every figure passes through the `figure-crop` queue before it is attached (A4).
Bbox precision from a model is B8 — unmeasured — and a wrong crop is the kind of
error that looks fine in the item YAML and wrong only on the page.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import cv2

from knowledge_base.models.item import Figure, FigureOrigin, Item
from knowledge_base.ops.log import get
from knowledge_base.pipeline.queues import Queues

log = get("figures")

PADDING_PX = 12


@dataclass
class Crop:
    path: Path
    bbox: list[float]
    from_embedded: bool


def crop_region(source: Path, bbox: list[float], dest: Path,
                padding: int = PADDING_PX) -> Crop:
    image = cv2.imread(str(source), cv2.IMREAD_UNCHANGED)
    if image is None:
        raise ValueError(f"unreadable capture: {source}")
    height, width = image.shape[:2]
    x, y, w, h = (float(v) for v in bbox)
    left = max(0, int(x) - padding)
    top = max(0, int(y) - padding)
    right = min(width, int(x + w) + padding)
    bottom = min(height, int(y + h) + padding)
    if right <= left or bottom <= top:
        raise ValueError(f"empty crop for bbox {bbox} in a {width}x{height} capture")
    dest.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(dest), image[top:bottom, left:right])
    return Crop(path=dest, bbox=[left, top, right - left, bottom - top],
                from_embedded=False)


def pick_embedded(embedded: list[Path], bbox: list[float]) -> Path | None:
    """Prefer a publisher-embedded image when one plausibly covers the bbox.

    "Plausibly" is deliberate: an embedded image carries no page coordinates
    here, so the choice is by aspect ratio and is a *suggestion* the review gate
    confirms. Guessing silently is what the gate exists to prevent.
    """
    if not embedded:
        return None
    _, _, w, h = (float(v) for v in bbox)
    if h <= 0:
        return None
    target = w / h
    best, best_error = None, None
    for path in embedded:
        image = cv2.imread(str(path), cv2.IMREAD_UNCHANGED)
        if image is None or image.shape[0] == 0:
            continue
        error = abs((image.shape[1] / image.shape[0]) - target)
        if best_error is None or error < best_error:
            best, best_error = path, error
    return best if best_error is not None and best_error < 0.25 else None


def queue_for_review(item: Item, crop: Crop, capture_id: str, queues: Queues) -> None:
    queues.add("figure-crop", {
        "item": item.id, "capture_id": capture_id, "bbox": crop.bbox,
        "asset": str(crop.path), "from_embedded": crop.from_embedded,
        "why": "figure bboxes are model-supplied and unmeasured (B8); a wrong crop "
               "looks correct in the item and wrong only on the page"})


def attach(item: Item, asset_name: str, provenance_index: int,
           bbox: list[float], caption: str | None = None) -> Item:
    """Attach an approved figure. Called after the review gate, never before."""
    figure = Figure(asset=asset_name, caption=caption,
                    origin=FigureOrigin(provenance_index=provenance_index, bbox=bbox))
    return item.model_copy(update={"figures": [*item.figures, figure]})
