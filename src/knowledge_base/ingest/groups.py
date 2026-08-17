"""Capture groups (§I-6.5) — which captures were taken together.

A group is the unit of extraction batching and of continuation context. Three
kinds of capture resolve it three different ways:

* **textbook x pdf** — contiguous page runs within one document.
* **textbook x raster** — one group per *sync drop* (the set of new files a
  single sync observed, from the registry's first-seen timestamp). Deterministic,
  and independent of filenames and of file timestamps.
* **board x photo** — session identity by explicit precedence, because upload
  timestamps demonstrably do not carry it: one real upload batch merged five
  lectures inside fifteen minutes (docs/FINDINGS.md, "Session grouping and
  volume").

The board precedence, in order:

  1. a dated subfolder under `Lecture-Boards/` — structural and unfalsifiable;
  2. EXIF `DateTimeOriginal` read from the file bytes;
  3. a parseable date in the filename — verified correct on 200/200 real board
     photographs. The standing rule against parsing filenames was given about
     *screenshots*, which have no shared convention across devices;
  4. the file timestamp, **with a warning** — known-wrong, and present only so
     that a run never halts.

Whatever resolves it, the answer is written into the registry once and read
forever after (A26).
"""

from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone
from pathlib import Path, PurePosixPath

from knowledge_base.config import Settings
from knowledge_base.ingest import exif
from knowledge_base.ingest.registry import Entry, Registry
from knowledge_base.ops.log import get

log = get("groups")

# Signals, in the order the precedence tries them.
FOLDER, EXIF_DATE, FILENAME, FILE_MTIME = "folder", "exif", "filename", "mtime"

_DATE_PATTERNS = [
    # Anchored to a non-digit boundary so a serial number cannot masquerade
    # as a date. Ordered most-specific first.
    (re.compile(r"(?<!\d)(20\d{2})[-_.]?(\d{2})[-_.]?(\d{2})(?!\d)"), (1, 2, 3)),
    (re.compile(r"(?<!\d)(\d{2})[-_.](\d{2})[-_.](20\d{2})(?!\d)"), (3, 2, 1)),
]
_FOLDER_DATE = re.compile(r"^(20\d{2})[-_.]?(\d{2})[-_.]?(\d{2})")


def date_in_name(name: str) -> datetime | None:
    for pattern, (y, m, d) in _DATE_PATTERNS:
        hit = pattern.search(name)
        if not hit:
            continue
        try:
            return datetime(int(hit.group(y)), int(hit.group(m)), int(hit.group(d)))
        except ValueError:
            continue
    return None


def dated_subfolder(rel_path: str, board_folder: str) -> str | None:
    """The first path component under `Lecture-Boards/` that reads as a date."""
    parts = PurePosixPath(rel_path).parts
    if not parts or parts[0] != board_folder or len(parts) < 3:
        return None
    hit = _FOLDER_DATE.match(parts[1])
    return f"{hit.group(1)}-{hit.group(2)}-{hit.group(3)}" if hit else None


def resolve_board_group(
    entry: Entry, abs_path: Path, settings: Settings, session_gap: timedelta | None = None,
    peers: list[Entry] | None = None,
) -> tuple[str, str, bool]:
    """Return (group, signal, warning) for one board photograph."""
    folder = dated_subfolder(entry.path, settings.capture_folders.board)
    if folder:
        return folder, FOLDER, False

    taken = exif.datetime_original(abs_path)
    if taken:
        return _session_key(taken, peers, session_gap or
                            timedelta(minutes=settings.groups.session_gap_minutes)), \
               EXIF_DATE, False

    named = date_in_name(PurePosixPath(entry.path).name)
    if named:
        return named.strftime("%Y-%m-%d"), FILENAME, False

    stamp = datetime.fromtimestamp(entry.mtime, tz=timezone.utc)
    log.warning("%s: no dated folder, no EXIF, no date in name — grouping by file "
                "timestamp, which is known to merge distinct lectures", entry.path)
    return stamp.strftime("%Y-%m-%d"), FILE_MTIME, True


def _session_key(taken: datetime, peers: list[Entry] | None, gap: timedelta) -> str:
    """Within EXIF-dated captures, split a day at gaps longer than `gap`.

    `session_gap_minutes` applies only to this step (§I-6.5). Two lectures on the
    same day are two sessions; two boards forty seconds apart are one.
    """
    day = taken.strftime("%Y-%m-%d")
    if not peers:
        return f"{day}-s1"
    same_day = sorted(
        t for t in (_exif_time(p) for p in peers) if t and t.strftime("%Y-%m-%d") == day
    )
    index, previous = 1, None
    for t in same_day:
        if previous is not None and t - previous > gap:
            index += 1
        if t >= taken:
            break
        previous = t
    return f"{day}-s{index}"


def _exif_time(entry: Entry) -> datetime | None:
    raw = entry.exif.get("DateTimeOriginal") or entry.exif.get("DateTime")
    if not isinstance(raw, str):
        return None
    try:
        return datetime.strptime(raw.strip(), "%Y:%m:%d %H:%M:%S")
    except ValueError:
        return None


def raster_group(first_seen: str) -> str:
    """One group per sync drop. `first_seen` is stamped by the sync, so every file
    a single sync observed shares it regardless of name or file time."""
    return f"drop-{first_seen}"


def pdf_groups(pages: list[int], source_key: str, max_pages: int) -> list[tuple[str, list[int]]]:
    """Contiguous page runs of at most `max_pages`, named after the run."""
    out: list[tuple[str, list[int]]] = []
    run: list[int] = []
    for p in sorted(pages):
        if run and (p != run[-1] + 1 or len(run) >= max_pages):
            out.append((f"{source_key}-pp{run[0]}-{run[-1]}", run))
            run = []
        run.append(p)
    if run:
        out.append((f"{source_key}-pp{run[0]}-{run[-1]}", run))
    return out


def assign(registry: Registry, field_key: str, settings: Settings, inbox: Path) -> int:
    """Resolve groups for every ungrouped capture in a field. Returns the count.

    Already-grouped captures are never revisited — that is the whole point of
    A26, and `Registry.set_group` refuses a regroup even if this is called twice.
    """
    pending = registry.ungrouped(field_key)
    boards = [e for e in pending if e.capture == "photo"]
    assigned = 0

    for e in pending:
        if e.capture == "photo":
            group, signal, warn = resolve_board_group(
                e, inbox / e.path, settings, peers=boards)
        elif e.capture == "raster":
            group, signal, warn = raster_group(e.first_seen), "drop", False
        else:  # pdf pages are grouped at batching time, by page run
            group, signal, warn = f"{e.source_key or 'unsorted'}-doc", "document", False
        registry.set_group(e.sha256, group, signal, warn)
        assigned += 1
    return assigned
