"""A single-instance lock for the nightly run (§I-12).

`flock` on a file, held for the process's lifetime. Two runs overlapping would
write the store concurrently, and the store is the one thing in this system that
cannot be regenerated from anything else.

Non-blocking on purpose: a second run arriving while the first is still going
should report that and exit, not queue up behind it and start an hour late.

On Windows, where `fcntl` does not exist, the same guarantee is provided by
`msvcrt.locking` with `LK_NBLCK`, which locks a byte range of the file
non-blockingly instead of the whole file. A second process attempting to lock
that same range fails immediately with `OSError`, exactly mirroring `flock`'s
`LOCK_NB` behaviour, so the two mechanisms are equivalent for this purpose.
"""

from __future__ import annotations

import os
from contextlib import contextmanager
from pathlib import Path

if os.name == "posix":
    import fcntl
else:
    import msvcrt

from knowledge_base.config import ROOT
from knowledge_base.ops.log import get

log = get("locks")

_LOCK_NBYTES = 1


class AlreadyRunning(RuntimeError):
    pass


@contextmanager
def run_lock(name: str = "nightly", root: Path = ROOT):
    path = Path(root) / "state" / f"{name}.lock"
    path.parent.mkdir(parents=True, exist_ok=True)
    handle = path.open("w", encoding="utf-8")
    locked = False
    try:
        try:
            if os.name == "posix":
                fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            else:
                handle.seek(0)
                msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, _LOCK_NBYTES)
            locked = True
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
            if locked:
                if os.name == "posix":
                    fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
                else:
                    handle.seek(0)
                    msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, _LOCK_NBYTES)
        finally:
            handle.close()
