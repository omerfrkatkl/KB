"""The item store — one YAML file per item under `fields/<field>/items/<ulid>.yaml`.

Design constraints, all of them consequences of "built once and used for decades":

* **Atomic writes.** temp file in the same directory, fsync, then `os.replace`.
  A half-written item file is corruption of the owner's originals-derived work,
  which is hard stop 2 in the autonomy protocol; the write path must make it
  impossible rather than unlikely.
* **One file per item.** A single store file would rewrite the whole corpus on
  every merge and turn every git diff into noise. Per-item files keep a merge
  visible as a merge.
* **Round-trip YAML.** `ruamel.yaml` in round-trip mode, block style, so a file
  the owner hand-edits with `kb edit` comes back looking like he left it.
"""

from __future__ import annotations

import io
import os
import subprocess
from pathlib import Path
from typing import Iterable, Iterator

from ruamel.yaml import YAML

from knowledge_base.config import ROOT
from knowledge_base.models.item import Item, Status, now
from knowledge_base.ops.log import get

log = get("store")


def _yaml() -> YAML:
    y = YAML()
    y.default_flow_style = False
    y.width = 100
    y.preserve_quotes = True
    return y


def _plain(obj):
    if hasattr(obj, "items"):
        return {str(k): _plain(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_plain(v) for v in obj]
    return obj


class Store:
    def __init__(self, field: str, root: Path = ROOT):
        self.field = field
        self.root = Path(root)
        self.dir = self.root / "fields" / field / "items"
        self.assets = self.root / "fields" / field / "assets"

    # ── paths ─────────────────────────────────────────────────────────
    def path(self, item_id: str) -> Path:
        return self.dir / f"{item_id}.yaml"

    def asset_dir(self, item_id: str) -> Path:
        return self.assets / item_id

    # ── read ──────────────────────────────────────────────────────────
    def exists(self, item_id: str) -> bool:
        return self.path(item_id).exists()

    def get(self, item_id: str) -> Item:
        return self._read(self.path(item_id))

    def _read(self, p: Path) -> Item:
        return Item.model_validate(_plain(_yaml().load(p.read_text(encoding="utf-8"))))

    def ids(self) -> list[str]:
        if not self.dir.exists():
            return []
        return sorted(p.stem for p in self.dir.glob("*.yaml"))

    def all(self) -> Iterator[Item]:
        for i in self.ids():
            yield self.get(i)

    def index(self) -> dict[str, Item]:
        """Whole-field load. The corpus is thousands of small files, not millions;
        a full read is milliseconds and removes a whole class of staleness bug."""
        return {i.id: i for i in self.all()}

    def buildable(self) -> list[Item]:
        """What a build may render: active only. `open` items are incomplete and
        `flagged` items are awaiting a ruling; neither reaches the PDF."""
        return [i for i in self.all() if i.status is Status.ACTIVE]

    # ── write ─────────────────────────────────────────────────────────
    def put(self, item: Item) -> Path:
        if item.field != self.field:
            raise ValueError(f"item {item.id} belongs to field {item.field}, not {self.field}")
        self.dir.mkdir(parents=True, exist_ok=True)
        p = self.path(item.id)
        # mode="json" renders enums as their values and datetimes as ISO strings,
        # so the file is plain YAML with no Python-specific tags in it.
        payload = item.model_dump(mode="json", exclude_none=False)
        buf = io.StringIO()
        _yaml().dump(payload, buf)
        _atomic_write(p, buf.getvalue())
        return p

    def touch(self, item: Item) -> Item:
        return item.model_copy(update={"updated": now()})

    def supersede(self, item_id: str, by: str) -> Item:
        """Never delete. A superseded item keeps its provenance forever (§I-3)."""
        it = self.get(item_id)
        it = it.model_copy(update={
            "status": Status.SUPERSEDED, "superseded_by": by, "updated": now()})
        self.put(it)
        return it


def _atomic_write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8", newline="") as fh:
        fh.write(text)
        fh.flush()
        os.fsync(fh.fileno())
    os.replace(tmp, path)
    # fsync the directory too: replace() is atomic, but its durability across a
    # power loss is not guaranteed until the directory entry is on disk.
    # Only POSIX allows this: a directory can be opened as a file descriptor and
    # fsynced, and that is what makes the rename itself durable. Windows exposes
    # no equivalent through the standard library — opening a directory fails — so
    # there the content fsync above still applies and the durability of the
    # rename is left to the operating system.
    if os.name == "posix":
        fd = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(fd)
        finally:
            os.close(fd)


# ── git helper ────────────────────────────────────────────────────────

def commit(paths: Iterable[Path], message: str, root: Path = ROOT) -> bool:
    """Commit the given paths. Returns False when there was nothing to commit.

    The store is tracked (A13), so every automated change lands as a reviewable
    commit rather than as an unexplained working-tree diff the next morning.
    """
    rel = [str(Path(p).resolve().relative_to(Path(root).resolve())) for p in paths]
    if not rel:
        return False
    inside = subprocess.run(["git", "rev-parse", "--is-inside-work-tree"],
                            cwd=root, capture_output=True, text=True)
    if inside.returncode != 0:
        # Committing makes the store reviewable; it is not what makes it correct.
        # A run must not fail — and must not discard extracted work — because the
        # store happens not to be tracked.
        log.warning("%s is not a git work tree — skipping the commit", root)
        return False
    added = subprocess.run(["git", "add", "--", *rel], cwd=root,
                           capture_output=True, text=True)
    if added.returncode != 0:
        log.warning("git add failed: %s", added.stderr.strip())
        return False
    staged = subprocess.run(["git", "diff", "--cached", "--quiet", "--", *rel],
                            cwd=root, capture_output=True, text=True)
    if staged.returncode == 0:
        return False
    r = subprocess.run(["git", "commit", "-m", message, "--", *rel],
                       cwd=root, capture_output=True, text=True)
    if r.returncode != 0:
        log.error("git commit failed: %s", r.stderr.strip())
        return False
    return True
