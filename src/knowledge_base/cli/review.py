"""`knowledge-base review` — one decision per screen (§I-10).

Every ruling appends to `decisions.log`, append-only. That log is the human
judgment layer made auditable and replayable: years from now the question "why is
this term canonical" has an answer with a date on it.

The UI is deliberately small. Each queue gets a fixed option set — the one the
plan names — and there is no free-text path that would let a ruling be recorded
in a form nothing can replay.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from knowledge_base.config import ROOT
from knowledge_base.pipeline.queues import QueueEntry, Queues

console = Console()

DECISIONS_LOG = "decisions.log"


@dataclass
class Ruling:
    queue: str
    entry_id: str
    choice: str
    payload: dict
    at: str


def log_path(root: Path = ROOT) -> Path:
    return Path(root) / DECISIONS_LOG


def record_ruling(ruling: Ruling, root: Path = ROOT) -> None:
    """Append-only. Never rewritten, never compacted."""
    path = log_path(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(ruling.__dict__, sort_keys=True) + "\n")


def read_rulings(root: Path = ROOT) -> list[Ruling]:
    path = log_path(root)
    if not path.exists():
        return []
    return [Ruling(**json.loads(line)) for line in path.read_text().splitlines() if line]


# ── per-queue options ─────────────────────────────────────────────────

OPTIONS: dict[str, list[str]] = {
    "new-term": ["canonical", "ban", "skip"],
    "near-duplicate": ["merge-keep-A", "merge-keep-B", "keep-both",
                       "keep-both-proofs", "skip"],
    "unclassified": ["accept-as-remark", "discard-as-excluded", "skip"],
    "unsorted-source": ["assign-source", "skip"],
    "new-source": ["register", "skip"],
    "low-resolution": ["recapture", "extract-anyway", "skip"],
    "pending-ref": ["resolve", "leave-open", "skip"],
    "audit-gap": ["re-extract", "accept-gap", "skip"],
    "figure-crop": ["accept", "adjust", "reject", "skip"],
    "open-gone-quiet": ["close-as-is", "keep-waiting", "discard", "skip"],
    "relint-ambiguous": ["substitute", "leave", "skip"],
}


def render(entry: QueueEntry) -> Panel:
    table = Table(show_header=False, box=None, pad_edge=False)
    for key, value in entry.payload.items():
        text = value if isinstance(value, str) else json.dumps(value, default=str)
        table.add_row(f"[bold]{key}[/bold]", text[:400])
    return Panel(table, title=f"{entry.kind} · {entry.id}", subtitle=entry.created)


def work(queues: Queues, ask: Callable[[QueueEntry, list[str]], str],
         only: str | None = None, root: Path = ROOT) -> int:
    """Walk the queues, ask for a ruling on each entry, record and resolve it.

    `ask` is injected so the loop is testable without a terminal. The review
    session is the one place a wrong keystroke costs a ruling, and a loop that
    can only be exercised by hand is a loop nobody exercises.
    """
    ruled = 0
    names = [only] if only else [n for n in OPTIONS if queues.list(n)]
    for name in names:
        for entry in queues.list(name):
            options = OPTIONS.get(name, ["skip"])
            choice = ask(entry, options)
            if choice not in options:
                raise ValueError(f"{choice!r} is not an option for {name}: {options}")
            if choice == "skip":
                continue
            record_ruling(Ruling(queue=name, entry_id=entry.id, choice=choice,
                                 payload=entry.payload,
                                 at=datetime.now(timezone.utc).isoformat(
                                     timespec="seconds")), root)
            queues.resolve(name, entry.id)
            ruled += 1
    return ruled


def interactive(entry: QueueEntry, options: list[str]) -> str:
    from rich.prompt import Prompt

    console.print(render(entry))
    return Prompt.ask("ruling", choices=options, default="skip")
