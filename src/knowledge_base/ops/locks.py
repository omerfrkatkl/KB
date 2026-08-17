"""A single-instance lock for the nightly run (§I-12).

`flock` on a file, held for the process's lifetime. Two runs overlapping would
write the store concurrently, and the store is the one thing in this system that
cannot be regenerated from anything else.

Non-blocking on purpose: a second run arriving while the first is still going
should report that and exit, not queue up behind it and start an hour late.
"""

from __future__ import annotations

import fcntl
import os
from contextlib import contextmanager
from pathlib import Path

from knowledge_base.config import ROOT
from knowledge_base.ops.log import get

log = get("locks")


class AlreadyRunning(RuntimeError):
    pass


@contextmanager
def run_lock(name: str = "nightly", root: Path = ROOT):
    path = Path(root) / "state" / f"{name}.lock"
    path.parent.mkdir(parents=True, exist_ok=True)
    handle = path.open("w")
    try:
        try:
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as e:
            raise AlreadyRunning(
                f"another {name} run holds {path}. Two runs would write the store "
                "concurrently; the store is the one artefact nothing can regenerate."
            ) from e
        handle.write(f"{os.getpid()}\n")
        handle.flush()
        yield path
    finally:
        try:
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
        finally:
            handle.close()
