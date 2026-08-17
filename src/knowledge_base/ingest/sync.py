"""Ingestion driver (§I-6) and the Drive sync that feeds it.

`ingest_field` is the part that runs anywhere: walk `inbox/<field>`, hash every
file, route it, gate it, group it, and record it. `sync_field` is the rclone
half, which needs Drive and a configured remote.

Ordering note (§I-6.5): ingestion order is **not** a correctness dependency for
textbook captures. Placement in the book comes from `topic` + `outline.yaml`, and
continuation matches fragments by content against the open-item set. A drop of
screenshots in arbitrary order produces the same book as the same drop in perfect
order.
"""

from __future__ import annotations

import shutil
import subprocess
from dataclasses import dataclass
from dataclasses import field as dc_field
from datetime import datetime, timezone
from pathlib import Path

from knowledge_base.config import ROOT, Settings
from knowledge_base.ingest import exif, groups
from knowledge_base.ingest.registry import Entry, Registry, sha256_of
from knowledge_base.ingest.resolution import gate
from knowledge_base.ingest.route import RoutingError, route
from knowledge_base.ops.log import get
from knowledge_base.pipeline.queues import Queues

log = get("ingest")

READABLE = {".pdf", ".jpg", ".jpeg", ".png", ".heic", ".heif", ".tif", ".tiff", ".webp"}


@dataclass
class IngestReport:
    field: str
    seen: int = 0
    new: int = 0
    skipped_known: int = 0
    unreadable: list[str] = dc_field(default_factory=list)
    unrouted: list[str] = dc_field(default_factory=list)
    low_resolution: list[str] = dc_field(default_factory=list)
    unsorted: list[str] = dc_field(default_factory=list)
    new_sources: list[str] = dc_field(default_factory=list)
    grouped: int = 0

    def summary(self) -> str:
        return (f"{self.field}: {self.seen} files, {self.new} new, "
                f"{self.skipped_known} already known, {self.grouped} grouped; "
                f"{len(self.low_resolution)} below the resolution floor, "
                f"{len(self.unrouted)} unrouted")


def sync_field(field_key: str, settings: Settings, root: Path = ROOT,
               dry_run: bool = False) -> subprocess.CompletedProcess:
    """`rclone sync <remote>:<field.captures> inbox/<field> --checksum` (§I-6.1).

    `--checksum` rather than size+mtime: a file copied between machines loses its
    timestamp, and the registry is keyed on content anyway.
    """
    dest = settings.inbox(field_key, root)
    dest.mkdir(parents=True, exist_ok=True)
    remote = f"{settings.drive_remote}:{settings.fields[field_key].captures}"
    cmd = ["rclone", "sync", remote, str(dest), "--checksum"]
    if dry_run:
        cmd.append("--dry-run")
    log.info("sync %s -> %s", remote, dest)
    return subprocess.run(cmd, capture_output=True, text=True)


def publish(paths: list[Path], settings: Settings) -> subprocess.CompletedProcess:
    """`rclone copy` the built PDFs and the run report back to Drive (§I-6.1)."""
    remote = f"{settings.drive_remote}:{settings.output_folder}"
    cmd = ["rclone", "copy", *[str(p) for p in paths], remote]
    log.info("publish %d file(s) -> %s", len(paths), remote)
    return subprocess.run(cmd, capture_output=True, text=True)


def ingest_field(
    field_key: str, settings: Settings, root: Path = ROOT,
    registry: Registry | None = None, queues: Queues | None = None,
) -> IngestReport:
    inbox = settings.inbox(field_key, root)
    reg = registry or Registry(root)
    q = queues or Queues(root)
    report = IngestReport(field=field_key)
    drop_stamp = datetime.now(timezone.utc).isoformat(timespec="seconds")
    unsorted_files: list[str] = []

    for path in sorted(p for p in inbox.rglob("*") if p.is_file()):
        report.seen += 1
        if path.suffix.lower() not in READABLE:
            report.unreadable.append(str(path.relative_to(inbox)))
            continue

        digest = sha256_of(path)
        if reg.known(digest):
            report.skipped_known += 1
            continue

        try:
            r = route(path, inbox, settings)
        except RoutingError as e:
            # Not a hard stop: the file stays in the inbox untouched and is
            # reported. Discarding it, or guessing its kind, would be worse —
            # `kind` decides the exam star.
            log.warning("unrouted: %s", e)
            report.unrouted.append(str(path.relative_to(inbox)))
            continue

        rel = path.relative_to(inbox).as_posix()
        entry = Entry(
            sha256=digest, path=rel, field_key=field_key,
            kind=r.kind.value, capture=r.capture.value,
            source_key=r.source_key, unsorted=r.unsorted,
            size=path.stat().st_size, mtime=path.stat().st_mtime,
            first_seen=drop_stamp,
            exif=exif.read(path) if r.capture.value != "pdf" else {},
        )

        if r.capture.value in ("photo", "raster"):
            m = gate(path, settings.resolution_floor_px)
            entry.text_height_px = m.text_height_px
            entry.low_resolution = not m.passes
            if not m.passes:
                report.low_resolution.append(rel)
                q.add("low-resolution", {
                    "field": field_key, "path": rel,
                    "text_height_px": round(m.text_height_px, 1),
                    "floor_px": m.floor_px,
                    "why": "a capture below the floor cannot be trusted to preserve "
                           "subscripts, primes, and integral bounds",
                }, context_paths=[path])

        reg.record(entry)
        report.new += 1

        if r.unsorted:
            unsorted_files.append(rel)
        elif r.source_key and not _source_registered(r.source_key, field_key, root):
            if r.source_key not in report.new_sources:
                report.new_sources.append(r.source_key)

    # A25: ONE queue entry per drop, naming the files — not one per file.
    if unsorted_files:
        report.unsorted = unsorted_files
        q.add("unsorted-source", {
            "field": field_key, "drop": drop_stamp, "files": unsorted_files,
            "why": "captures in Texts/Unsorted/ carry no source identity; items from "
                   "them stay flagged until this is answered (A25)",
        }, entry_id=f"unsorted-{field_key}-{drop_stamp}")

    for key in report.new_sources:
        q.add("new-source", {
            "field": field_key, "source_key": key,
            "needs": ["title", "citation", "rank", "conventions"],
            "why": "one-time source metadata; the conventions block is embedded in "
                   "this source's prompts thereafter",
        }, entry_id=f"new-source-{field_key}-{key}")

    report.grouped = groups.assign(reg, field_key, settings, inbox)
    reg.save()
    log.info("%s", report.summary())
    return report


def _source_registered(key: str, field_key: str, root: Path) -> bool:
    from knowledge_base.models.profile import Sources, _read, profile_dir

    sources = _read(profile_dir(field_key, root) / "sources.yaml", Sources, default={})
    return sources.get(key) is not None


def have_rclone() -> bool:
    return shutil.which("rclone") is not None
