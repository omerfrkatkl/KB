"""Logging. One run, one log file, plus a console stream.

Every pipeline stage writes here; `report.md` is assembled from the same run id,
so a line in the report can always be traced back to the line that produced it.
"""

from __future__ import annotations

import logging
import os
from datetime import datetime, timezone

from knowledge_base.config import ROOT

LOGS = ROOT / "logs"
_CONFIGURED = False


def run_id() -> str:
    """Stable within a process; overridable so a resumed run keeps its log."""
    rid = os.environ.get("KB_RUN_ID")
    if not rid:
        rid = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        os.environ["KB_RUN_ID"] = rid
    return rid


def setup(level: int = logging.INFO, to_file: bool = True) -> logging.Logger:
    global _CONFIGURED
    root = logging.getLogger("kb")
    if _CONFIGURED:
        return root
    root.setLevel(level)
    fmt = logging.Formatter("%(asctime)s %(levelname)-7s %(name)s  %(message)s")

    console = logging.StreamHandler()
    console.setFormatter(fmt)
    root.addHandler(console)

    if to_file:
        LOGS.mkdir(parents=True, exist_ok=True)
        fh = logging.FileHandler(LOGS / f"{run_id()}.log", encoding="utf-8")
        fh.setFormatter(fmt)
        root.addHandler(fh)

    root.propagate = False
    _CONFIGURED = True
    return root


def get(name: str) -> logging.Logger:
    setup()
    return logging.getLogger(f"kb.{name}")
