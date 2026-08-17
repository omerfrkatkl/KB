"""The capture registry — `state/progress.json` (§I-6.2).

Every file the pipeline has ever seen, keyed by sha256. Three jobs:

1. **Never reprocess.** An identical hash is skipped, so a re-sync of Drive costs
   nothing and a file copied to a second location is not extracted twice.
2. **Carry the routing decision forward.** `kind`, `capture`, `source_key`.
3. **Persist session identity (A26).** The group a capture belongs to is resolved
   *once*, at first ingestion, and read thereafter. The signals it is derived
   from are not stable over a lifetime — a new phone may stop writing EXIF, a
   capture app may change its filenames, a copied file loses its timestamp — so
   re-deriving would silently regroup years-old captures and break continuation
   links that were correct when they were made.

The registry is written atomically for the same reason the store is: it is the
only record that a capture was ever processed.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from knowledge_base.config import ROOT
from knowledge_base.ops.log import get

log = get("registry")


@dataclass
class Entry:
    sha256: str
    path: str                     # inbox-relative, POSIX
    field_key: str
    kind: str
    capture: str
    source_key: str | None
    unsorted: bool
    size: int
    mtime: float
    first_seen: str               # defines raster capture groups (§I-6.5)
    group: str | None = None      # resolved once (A26), then read
    group_signal: str | None = None   # which precedence step produced it
    group_warning: bool = False   # step 4 fired: known-wrong, run continues
    exif: dict[str, Any] = field(default_factory=dict)
    extracted: bool = False
    text_height_px: float | None = None   # resolution gate measurement
    low_resolution: bool = False


def sha256_of(path: Path) -> str:
    h = hashlib.sha256()
    with Path(path).open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


class Registry:
    def __init__(self, root: Path = ROOT):
        self.root = Path(root)
        self.path = self.root / "state" / "progress.json"
        self.entries: dict[str, Entry] = {}
        self.load()

    # ── persistence ───────────────────────────────────────────────────
    def load(self) -> None:
        if not self.path.exists():
            self.entries = {}
            return
        raw = json.loads(self.path.read_text(encoding="utf-8"))
        self.entries = {k: Entry(**v) for k, v in raw.get("captures", {}).items()}

    def save(self) -> None:
        payload = {
            "version": 1,
            "updated": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "captures": {k: asdict(v) for k, v in sorted(self.entries.items())},
        }
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(payload, indent=2, sort_keys=False), encoding="utf-8",
                       newline="")
        tmp.replace(self.path)

    # ── queries ───────────────────────────────────────────────────────
    def known(self, digest: str) -> bool:
        return digest in self.entries

    def get(self, digest: str) -> Entry | None:
        return self.entries.get(digest)

    def by_field(self, field_key: str) -> list[Entry]:
        return [e for e in self.entries.values() if e.field_key == field_key]

    def ungrouped(self, field_key: str) -> list[Entry]:
        return [e for e in self.by_field(field_key) if e.group is None]

    def in_group(self, group: str) -> list[Entry]:
        return sorted((e for e in self.entries.values() if e.group == group),
                      key=lambda e: (e.first_seen, e.path))

    # ── mutation ──────────────────────────────────────────────────────
    def record(self, entry: Entry) -> Entry:
        """Insert a capture. An already-known hash is returned unchanged —
        never re-routed and never re-grouped (A26)."""
        existing = self.entries.get(entry.sha256)
        if existing:
            return existing
        self.entries[entry.sha256] = entry
        return entry

    def set_group(self, digest: str, group: str, signal: str, warning: bool = False) -> None:
        e = self.entries[digest]
        if e.group is not None:
            # A26: resolved once. Re-deriving is the defect this guards against.
            if e.group != group:
                log.warning("refusing to regroup %s: %s -> %s (A26)", e.path, e.group, group)
            return
        e.group, e.group_signal, e.group_warning = group, signal, warning

    def mark_extracted(self, digest: str) -> None:
        self.entries[digest].extracted = True
