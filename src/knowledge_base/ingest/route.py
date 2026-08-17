"""Routing: which `kind` and which `capture` a file has (§I-6.3, A23/A24).

Two independent axes, from two independent signals:

* **kind** — semantic — comes from the *folder*: `Lecture-Boards/**` is board,
  `Texts/**` is textbook. Never from the image. `kind` decides the exam star, and
  an image of a board photographed from a book page looks exactly like a board.
* **capture** — geometric — comes from the *file*: `.pdf` is pdf, an image with
  EXIF camera tags (Make/Model) is a photo, an image without them is a raster.

**No filename pattern is ever parsed here.** Device naming has no convention
across the owner's phone, his screenshot tool, and whatever he uses in five
years. The one place a filename is consulted is session grouping (`groups.py`),
where it sits *below* two structural signals and was verified against the real
corpus first.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path, PurePosixPath

from knowledge_base.config import Settings
from knowledge_base.ingest.exif import camera_tags
from knowledge_base.models.item import Capture, Kind

IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".heic", ".heif", ".tif", ".tiff", ".webp"}
PDF_SUFFIXES = {".pdf"}


class RoutingError(Exception):
    """The file is under neither capture folder, or is of a type we do not read."""


@dataclass(frozen=True)
class Route:
    kind: Kind
    capture: Capture
    source_key: str | None   # from Texts/<Source-Name>/; None for boards and Unsorted
    unsorted: bool           # A25: ingest normally, hold `source` null, queue once


def _rel_parts(path: Path, field_inbox: Path) -> tuple[str, ...]:
    try:
        rel = Path(path).resolve().relative_to(Path(field_inbox).resolve())
    except ValueError as e:
        raise RoutingError(f"{path} is not inside {field_inbox}") from e
    return PurePosixPath(rel.as_posix()).parts


def classify_capture(path: Path) -> Capture:
    suffix = Path(path).suffix.lower()
    if suffix in PDF_SUFFIXES:
        return Capture.PDF
    if suffix not in IMAGE_SUFFIXES:
        raise RoutingError(f"{path}: unreadable capture type {suffix!r}")
    return Capture.PHOTO if camera_tags(path) else Capture.RASTER


def route(path: Path, field_inbox: Path, settings: Settings) -> Route:
    parts = _rel_parts(path, field_inbox)
    if len(parts) < 2:
        raise RoutingError(
            f"{path}: a capture must sit under {settings.capture_folders.board}/ or "
            f"{settings.capture_folders.textbook}/ — the folder is what supplies `kind`")

    head, rest = parts[0], parts[1:]
    capture = classify_capture(path)

    if head == settings.capture_folders.board:
        return Route(kind=Kind.BOARD, capture=capture, source_key=None, unsorted=False)

    if head == settings.capture_folders.textbook:
        unsorted_leaf = PurePosixPath(settings.capture_folders.unsorted).parts[-1]
        if not rest or len(rest) < 2:
            raise RoutingError(
                f"{path}: textbook captures live under "
                f"{settings.capture_folders.textbook}/<Source-Name>/ (A25)")
        if rest[0] == unsorted_leaf:
            return Route(kind=Kind.TEXTBOOK, capture=capture, source_key=None, unsorted=True)
        return Route(kind=Kind.TEXTBOOK, capture=capture,
                     source_key=source_key(rest[0]), unsorted=False)

    raise RoutingError(
        f"{path}: top-level folder {head!r} is neither "
        f"{settings.capture_folders.board!r} nor {settings.capture_folders.textbook!r}")


def source_key(folder_name: str) -> str:
    """`Brown & Churchill 9e` -> `brown-churchill-9e`.

    The folder name is the source *identity* (A25), so the mapping must be
    stable: two folders that differ only in punctuation or case are the same
    source, and a source registered years ago must still resolve.
    """
    out = []
    for ch in folder_name.strip().lower():
        if ch.isalnum():
            out.append(ch)
        elif out and out[-1] != "-":
            out.append("-")
    return "".join(out).strip("-")
