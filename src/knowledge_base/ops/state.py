"""Per-stage run state (§I-12) — what finished, what did not, and where to resume.

Stages are idempotent, so resuming is re-running rather than continuing from a
saved cursor. This file records *what happened*, which is what the report is
assembled from and what a kill-mid-run resume consults to know it can skip a
stage that already completed in this run.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from knowledge_base.config import ROOT

STAGES = ("sync", "ingest", "extract", "validate", "audit", "commit",
          "build", "publish", "report")


@dataclass
class StageState:
    name: str
    status: str = "pending"      # pending | running | done | failed | skipped
    started: str | None = None
    finished: str | None = None
    detail: dict = field(default_factory=dict)
    error: str | None = None


@dataclass
class RunState:
    run_id: str
    stages: dict[str, StageState] = field(default_factory=dict)

    @classmethod
    def load(cls, run_id: str, root: Path = ROOT) -> "RunState":
        path = _path(run_id, root)
        if not path.exists():
            return cls(run_id=run_id,
                       stages={s: StageState(name=s) for s in STAGES})
        raw = json.loads(path.read_text(encoding="utf-8"))
        return cls(run_id=raw["run_id"],
                   stages={k: StageState(**v) for k, v in raw["stages"].items()})

    def save(self, root: Path = ROOT) -> None:
        path = _path(self.run_id, root)
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = {"run_id": self.run_id,
                   "updated": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                   "stages": {k: asdict(v) for k, v in self.stages.items()}}
        tmp = path.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        tmp.replace(path)

    def begin(self, stage: str) -> StageState:
        s = self.stages.setdefault(stage, StageState(name=stage))
        s.status, s.started = "running", _now()
        return s

    def finish(self, stage: str, **detail) -> None:
        s = self.stages[stage]
        s.status, s.finished = "done", _now()
        s.detail.update(detail)

    def fail(self, stage: str, error: str) -> None:
        s = self.stages[stage]
        s.status, s.finished, s.error = "failed", _now(), error

    def skip(self, stage: str, why: str) -> None:
        s = self.stages.setdefault(stage, StageState(name=stage))
        s.status, s.error = "skipped", why

    def done(self, stage: str) -> bool:
        return self.stages.get(stage, StageState(name=stage)).status == "done"

    def failed_stages(self) -> list[str]:
        return [k for k, v in self.stages.items() if v.status == "failed"]


def _path(run_id: str, root: Path) -> Path:
    return Path(root) / "state" / "runs" / f"{run_id}.json"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")
