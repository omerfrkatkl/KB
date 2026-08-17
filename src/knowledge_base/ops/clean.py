"""Remove build/test/lint artifacts: build/, .pytest_cache/, .ruff_cache/, and every
__pycache__ directory found under the repository root.

It exists instead of a shell `rm -rf` command because there is no single shell that
runs the same way on both POSIX and Windows, and `**/__pycache__` is a bash
globstar pattern that plain `sh` does not expand — so the shell version was not
reliably correct on either platform.

    python -m knowledge_base.ops.clean
"""

from __future__ import annotations

import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]

# Fixed, top-level removal targets.
TARGETS = ["build", ".pytest_cache", ".ruff_cache"]

# Never descend into these while walking for __pycache__: .git and .venv are not
# ours to touch, and the store and its queues (fields/, generated/, queue/, state/,
# derived/, inbox/, logs/, tools/, fonts/) cannot be regenerated — an accidental
# match under any of them must not be deleted.
SKIP_DIRS = {
    ".git", ".venv", "fonts", "tools", "inbox", "derived",
    "state", "logs", "generated", "queue", "fields",
}


def find_pycache_dirs(root: Path) -> list[Path]:
    found: list[Path] = []
    stack = [root]
    while stack:
        current = stack.pop()
        try:
            entries = list(current.iterdir())
        except OSError:
            continue
        for entry in entries:
            if not entry.is_dir():
                continue
            if entry.name in SKIP_DIRS:
                continue
            if entry.name == "__pycache__":
                found.append(entry)
                continue
            stack.append(entry)
    return found


def remove(path: Path, count: list[int]) -> None:
    if not path.exists():
        return
    shutil.rmtree(path)
    print(path.relative_to(ROOT).as_posix())
    count[0] += 1


def main() -> int:
    count = [0]
    for name in TARGETS:
        remove(ROOT / name, count)
    for cache_dir in find_pycache_dirs(ROOT):
        remove(cache_dir, count)
    print(f"removed {count[0]} path(s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
