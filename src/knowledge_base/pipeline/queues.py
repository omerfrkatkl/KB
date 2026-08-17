"""Review queues (§I-10) — `queue/<name>/<id>.yaml`.

The queues are the system's one concession to human judgment, and they exist for
a single reason: **unclassifiable material must never be force-fitted**. A forced
fit is silent distortion and undetectable downstream, which is the one error that
regenerating cannot repair.

They are made *rare* rather than removed. Pre-seeding the lexicon from the rule
documents (WP1.4A) converts roughly 150 terminology rulings into decisions
already made, and registering a source or authoring the outline up front keeps
those queues empty. A filling queue is not a reason to stop a run.

Deduplication by `id`: re-running a stage must not multiply entries for the same
fact. The A25 unsorted-source case is stronger still — one entry per *drop*,
naming all its files, not one per file.
"""

from __future__ import annotations

import hashlib
import io
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from ruamel.yaml import YAML

from knowledge_base.config import ROOT

NAMES = (
    "new-term",
    "near-duplicate",
    "unclassified",
    "open-gone-quiet",
    "figure-crop",
    "new-source",
    "unsorted-source",
    "low-resolution",
    "pending-ref",
    "audit-gap",
    "relint-ambiguous",
)


@dataclass
class QueueEntry:
    kind: str
    created: str
    payload: dict[str, Any]
    context_paths: list[str]
    id: str


def _yaml() -> YAML:
    y = YAML()
    y.default_flow_style = False
    y.width = 100
    return y


def _plain(obj):
    if hasattr(obj, "items"):
        return {str(k): _plain(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_plain(v) for v in obj]
    return obj


class Queues:
    def __init__(self, root: Path = ROOT):
        self.root = Path(root) / "queue"

    def dir(self, name: str) -> Path:
        if name not in NAMES:
            raise KeyError(f"{name!r} is not a queue (§I-10). Queues are a closed set.")
        return self.root / name

    def add(
        self,
        name: str,
        payload: dict[str, Any],
        *,
        entry_id: str | None = None,
        context_paths: Iterable[Path | str] = (),
    ) -> Path:
        """Append an entry. An existing id is left untouched, so a re-run of a
        stage neither multiplies entries nor overwrites a partially-worked one."""
        d = self.dir(name)
        eid = entry_id or _digest(name, payload)
        path = d / f"{eid}.yaml"
        if path.exists():
            return path
        d.mkdir(parents=True, exist_ok=True)
        entry = QueueEntry(
            kind=name,
            created=datetime.now(timezone.utc).isoformat(timespec="seconds"),
            payload=payload,
            context_paths=[str(p) for p in context_paths],
            id=eid,
        )
        buf = io.StringIO()
        _yaml().dump({"kind": entry.kind, "created": entry.created, "id": entry.id,
                      "payload": entry.payload, "context_paths": entry.context_paths}, buf)
        tmp = path.with_suffix(".yaml.tmp")
        tmp.write_text(buf.getvalue(), encoding="utf-8")
        tmp.replace(path)
        return path

    def list(self, name: str) -> list[QueueEntry]:
        d = self.dir(name)
        if not d.exists():
            return []
        out = []
        for p in sorted(d.glob("*.yaml")):
            raw = _plain(_yaml().load(p.read_text(encoding="utf-8")))
            out.append(QueueEntry(
                kind=raw["kind"], created=raw["created"], payload=raw.get("payload", {}),
                context_paths=raw.get("context_paths", []), id=raw["id"]))
        return out

    def counts(self) -> dict[str, int]:
        return {n: len(self.list(n)) for n in NAMES}

    def resolve(self, name: str, entry_id: str) -> bool:
        """Remove a worked entry. The ruling itself is recorded in
        `decisions.log` by the review CLI — this only clears the pending work."""
        p = self.dir(name) / f"{entry_id}.yaml"
        if not p.exists():
            return False
        p.unlink()
        return True


def _digest(name: str, payload: dict[str, Any]) -> str:
    """Stable id from the entry's content, so the same fact queues once."""
    key = repr(sorted((k, repr(v)) for k, v in payload.items()))
    return f"{name}-{hashlib.sha256(key.encode()).hexdigest()[:12]}"
