"""The raster chain (§I-6.3b) — flat captures: screenshots of a page or section.

**Preprocessing here is deliberately empty.** No orientation fix, no quad
detection, no deskew, no perspective warp, no CLAHE. The pixels are already
rectified and high-contrast, and every one of those operations can only degrade
them. Quad detection in particular risks locking onto a figure box or a table
border and silently cropping content away — a loss that produces a plausible,
complete-looking extraction of less than the page.

So this module stages the file and measures it. That is the whole chain. Its
tests exist to prove the pass-through is byte-exact, because the temptation to
"just deskew a little" is what this file is defending against.

A raster capture may cover a fragment of a page, may overlap another capture, and
carries no page identity. All three are absorbed downstream: item-level dedup
merges the overlaps, and `locator` records whatever the capture shows.
"""

from __future__ import annotations

import shutil
from dataclasses import dataclass
from pathlib import Path

from knowledge_base.ingest.resolution import Measurement, gate


@dataclass(frozen=True)
class Staged:
    capture_id: str
    path: Path            # what the prompt will point the model at
    source_path: Path     # the immutable original
    measurement: Measurement


def stage(path: Path, capture_id: str, out_dir: Path, floor_px: int) -> Staged:
    """Copy the capture into `derived/` unchanged and measure it.

    The copy is not preprocessing — it exists so that `inbox/` is never opened
    for writing by anything downstream, and so a staged batch is reproducible
    after the inbox is re-synced.
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    dest = out_dir / f"{capture_id}{path.suffix.lower()}"
    shutil.copyfile(path, dest)
    return Staged(capture_id=capture_id, path=dest, source_path=path,
                  measurement=gate(dest, floor_px))
