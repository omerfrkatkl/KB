"""Batching and the context pack (§I-7).

A batch is a capture group, split to the configured size:

  textbook x pdf     contiguous page runs of at most `batching.pdf_pages`
  board x photo      at most `batching.board_crops` per group, in capture order
  textbook x raster  at most `batching.raster_captures` per drop, any order

Ordering within a raster drop is *not* a correctness dependency (§I-6.5) —
placement comes from `topic` plus the outline, and continuation matches fragments
by content. Group membership affects extraction-context quality, never the
result.

The context pack carries everything policy needs to reach the extractor in one
place: the taxonomy and its exclusion classes, JSON Schemas generated from the
models, the compiled lexicon and symbols, the style digest from the compiled
validators, the field's open items, a compact item index for duplicate
proposals, and the source's identifier -> ULID table so "by Theorem 2.4"
resolves to a stable ref rather than to a number that would be rendered.

The pack is assembled from the *same* artefacts that enforce policy downstream.
A second, hand-maintained copy would drift, and the drift would surface as a
retry loop on well-formed output.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from knowledge_base.config import Settings
from knowledge_base.extract import prompts
from knowledge_base.ingest.registry import Entry, Registry
from knowledge_base.models import schemas
from knowledge_base.models.item import Item, Status
from knowledge_base.models.profile import Profile
from knowledge_base.ops.log import get

log = get("batcher")

DIGEST_CHARS = 200
TRAILING_ITEMS = 10


@dataclass
class Capture:
    id: str
    path: Path
    kind: str
    capture: str
    source_key: str | None
    page: int | None = None


@dataclass
class Batch:
    batch_id: str
    field_key: str
    group: str
    kind: str
    capture: str
    source_key: str | None
    captures: list[Capture] = field(default_factory=list)

    def size(self) -> int:
        return len(self.captures)


def batches_for(field_key: str, registry: Registry, settings: Settings,
                inbox: Path) -> list[Batch]:
    """Every un-extracted capture, grouped and split to the configured sizes."""
    pending = [e for e in registry.by_field(field_key)
               if not e.extracted and not e.low_resolution and e.group]
    by_group: dict[str, list[Entry]] = {}
    for e in pending:
        by_group.setdefault(e.group, []).append(e)

    limits = {"pdf": settings.batching.pdf_pages,
              "photo": settings.batching.board_crops,
              "raster": settings.batching.raster_captures}

    out: list[Batch] = []
    for group in sorted(by_group):
        entries = sorted(by_group[group], key=lambda e: (e.first_seen, e.path))
        limit = limits.get(entries[0].capture, 6)
        for index in range(0, len(entries), limit):
            chunk = entries[index:index + limit]
            out.append(Batch(
                batch_id=f"{field_key}-{group}-b{index // limit + 1:02d}",
                field_key=field_key, group=group, kind=chunk[0].kind,
                capture=chunk[0].capture, source_key=chunk[0].source_key,
                captures=[Capture(id=f"c{i + 1}", path=inbox / e.path, kind=e.kind,
                                  capture=e.capture, source_key=e.source_key)
                          for i, e in enumerate(chunk)]))
    return out


def digest(item: Item) -> str:
    s = item.slots
    text = s.get("conclusion") or s.get("body") or s.get("term") or ""
    return text[:DIGEST_CHARS]


def item_index(items: list[Item]) -> list[dict]:
    """A compact index so the extractor can *propose* duplicates. It proposes;
    dedup decides (§I-4). Nothing here is a merge instruction."""
    return [{"id": i.id, "type": i.type.value, "title": i.title, "digest": digest(i)}
            for i in items]


def open_items(items: list[Item]) -> list[dict]:
    """§7.3 continuation: what an incoming fragment may be continuing."""
    out = []
    for i in items:
        if i.status is not Status.OPEN:
            continue
        out.append({"id": i.id, "type": i.type.value, "title": i.title,
                    "missing": _missing(i)})
    return out


def _missing(item: Item) -> str:
    for index, proof in enumerate(item.slots.get("proofs") or []):
        if not proof.get("conclusion"):
            return f"proofs[{index}] has steps but no conclusion"
        for block in ("base", "inductive", "existence", "uniqueness",
                      "forward", "backward", "subset", "superset"):
            b = proof.get(block)
            if isinstance(b, dict) and not b.get("steps") and not b.get("conclusion"):
                return f"proofs[{index}].{block} is declared but empty"
    return "structure incomplete"


def identifier_table(items: list[Item], source_key: str | None) -> list[dict]:
    """`Theorem 2.4` / `(2)` / `Sec. 1` -> ULID, for one source.

    Without this the extractor has no way to turn an explicit citation into a
    ref, and A16 forbids rendering the number itself — so the citation would be
    lost rather than merely deferred.
    """
    out = []
    for item in items:
        for p in item.provenance:
            if source_key and p.source != source_key:
                continue
            if p.locator:
                out.append({"identifier": p.locator, "id": item.id, "title": item.title})
    return out


def trailing(items: list[Item], source_key: str | None, group: str) -> list[dict]:
    """The last few items from the same source and group, for continuity."""
    same = [i for i in items
            if any(p.source == source_key and p.group == group for p in i.provenance)]
    return [{"type": i.type.value, "digest": digest(i)} for i in same[-TRAILING_ITEMS:]]


def taxonomy_block(profile: Profile) -> dict:
    """The one written policy both prompts render from."""
    return {
        "types": [{"key": t.key, "note": t.note} for t in profile.taxonomy.types],
        "excluded": [{"key": e.key, "definition": e.definition}
                     for e in profile.taxonomy.excluded],
    }


def style_rules(profile: Profile) -> list[str]:
    """A digest of the compiled validators, for the prompt.

    Dual consumption, not a second copy: the regex engine enforces these
    independently at §I-8 step 4A. Telling the extractor reduces retries; it
    does not replace the check.
    """
    seen: list[str] = []
    for rule in profile.validators.rules:
        if rule.kind == "forbidden":
            seen.append(rule.message)
        elif rule.fix:
            seen.append(rule.message)
    return seen


def build_context(batch: Batch, profile: Profile, items: list[Item],
                  settings: Settings, phase_types: list[str] | None = None) -> dict:
    """The extraction context pack for one batch."""
    types = phase_types or profile.taxonomy.keys()
    source = profile.sources.get(batch.source_key) if batch.source_key else None
    return prompts.extraction_context(
        batch_id=batch.batch_id,
        field={"key": profile.field, "title": settings.fields[profile.field].title},
        source={"key": batch.source_key,
                "conventions": source.conventions if source else None},
        captures=[{"id": c.id, "path": str(c.path), "kind": c.kind,
                   "capture": c.capture,
                   "source_title": source.title if source else None,
                   "page": c.page} for c in batch.captures],
        taxonomy=taxonomy_block(profile),
        schemas=schemas.for_types(types),
        lexicon={"canonical": sorted(profile.lexicon.canonical_terms()),
                 "banned": _banned_by_canonical(profile)},
        symbols=[{"form": f.always, "note": f.note or f.section}
                 for f in profile.symbols.forms],
        style_rules=style_rules(profile),
        open_items=open_items(items),
        item_index=item_index(items),
        identifier_table=identifier_table(items, batch.source_key),
        trailing_items=trailing(items, batch.source_key, batch.group),
        dialect=settings.dialect,
    )


def _banned_by_canonical(profile: Profile) -> dict[str, list[str]]:
    out: dict[str, list[str]] = {}
    for variant, canonical in profile.lexicon.banned.items():
        out.setdefault(canonical, []).append(variant)
    return {k: sorted(v) for k, v in sorted(out.items())}


def build_audit_context(batch: Batch, profile: Profile, extraction) -> dict:
    return prompts.audit_context(
        batch_id=batch.batch_id,
        captures=[{"id": c.id, "path": str(c.path), "kind": c.kind,
                   "capture": c.capture, "source_title": None, "page": c.page}
                  for c in batch.captures],
        items=[{"tmp_id": i.tmp_id, "type": i.type, "title": i.title,
                "has_proof": bool(i.slots.get("proofs")),
                "statement": (i.slots.get("conclusion") or i.slots.get("body")
                              or i.slots.get("term") or "")[:DIGEST_CHARS]}
               for i in extraction.items],
        coverage=[c.model_dump() for c in extraction.coverage],
        excluded=[{"key": e.key, "definition": e.definition}
                  for e in profile.taxonomy.excluded],
        fragments=[f.model_dump() for f in extraction.fragments],
        duplicates=[d.model_dump() for d in extraction.duplicates],
    )
