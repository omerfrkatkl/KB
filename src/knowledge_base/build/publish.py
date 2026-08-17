"""Building a field's book, end to end (§I-11).

`build_field` is the whole path from store to PDF: load, emit, compile. It runs
anywhere the vendored toolchain exists. Publishing to Drive is `ingest.sync`'s
`publish`, which needs rclone and is called by the nightly driver.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from knowledge_base.build import compile as C
from knowledge_base.build import emitter
from knowledge_base.config import ROOT, Settings
from knowledge_base.models.item import Item
from knowledge_base.models.profile import load_profile
from knowledge_base.ops.log import get
from knowledge_base.pipeline.store import Store

log = get("build")

TEMPLATE = ROOT / "template" / "template-star.typ"


@dataclass
class BuildResult:
    field: str
    typ: Path
    pdf: Path | None
    item_count: int
    stderr: str = ""

    @property
    def ok(self) -> bool:
        return self.pdf is not None


def build_field(field_key: str, settings: Settings, root: Path = ROOT,
                items: list[Item] | None = None) -> BuildResult:
    profile = load_profile(field_key, root)
    store = Store(field_key, root)
    renderable = items if items is not None else store.buildable()
    out_dir = Path(root) / "build" / field_key
    written = emitter.write(renderable, profile, settings.fields[field_key].title,
                            out_dir, Path(root) / "template" / TEMPLATE.name)

    if not C.available(root):
        log.warning("toolchain absent — emitted %s but did not compile", written["main"])
        return BuildResult(field=field_key, typ=written["main"], pdf=None,
                           item_count=len(renderable),
                           stderr="typst not installed or not on PATH")

    title = settings.fields[field_key].title.replace(" ", "-")
    result = C.compile_doc(written["main"], root=root, out=out_dir / f"{title}.pdf")
    return BuildResult(field=field_key, typ=written["main"], pdf=result.pdf,
                       item_count=len(renderable), stderr=result.stderr)
