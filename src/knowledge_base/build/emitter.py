"""emitter.py — the store rendered to Typst (§I-11).

Deterministic by construction: the same store state produces byte-identical
output, which is what makes the golden-file test meaningful and what keeps a
rebuild's git diff to the items that actually changed.

Three responsibilities, and no fourth:

* **Order** — chapters from `outline.yaml`, items within a topic by the §I-5
  ordering key. The emitter never invents an order from ingestion time.
* **Escaping** — Typst markup characters inside prose runs are escaped; math runs
  are passed through untouched, because their content *is* Typst.
* **Reference resolution** — `{ref:ulid}` becomes `@<label>`, with the label from
  the numbering simulation, which is at parity with the compiler (WP0.2).

The prose itself comes from `frames.py`. Nothing in this file composes a
sentence.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

from knowledge_base.build import frames
from knowledge_base.build.numbering_sim import simulate
from knowledge_base.models.item import Item, Status
from knowledge_base.models.profile import Profile
from knowledge_base.ops.log import get

log = get("emitter")

MATH_RUN = re.compile(r"\$[^$]*\$")
REF_TOKEN = re.compile(r"\{ref:([0-9A-HJKMNP-TV-Z]{26})\}")

# §I-11: prose runs escape these. `//` is escaped separately — it is Typst's
# line comment, and a stray one silently deletes the rest of the line.
ESCAPE = "\\#$[]{}@*_<>~`"


def escape(text: str) -> str:
    """Escape a prose run. Math runs never reach this function."""
    out = []
    for ch in text:
        if ch in ESCAPE:
            out.append("\\" + ch)
        else:
            out.append(ch)
    escaped = "".join(out)
    return escaped.replace("//", "\\/\\/")


def escape_prose(text: str) -> str:
    """Escape everything outside `$…$`, leaving math runs verbatim."""
    parts = MATH_RUN.split(text)
    maths = MATH_RUN.findall(text)
    out = []
    for i, part in enumerate(parts):
        out.append(escape(part))
        if i < len(maths):
            out.append(maths[i])
    return "".join(out)


def prepare(text: str, plan_: "Plan") -> str:
    """Make one slot string safe to hand to frames.

    Escaping happens **here**, on transcribed text, and not on frame output.
    That ordering is the whole point: slot text came from a model and must not be
    able to inject Typst, while `*term*`, `*Case 1:*` and `*(i)*` are markup the
    frames deliberately emit. Escaping after composition would strip exactly the
    structure the rule documents mandate.

    Reference tokens are resolved as part of the same pass, so that `@label`
    survives — escaping first would turn it into `\\@label`.
    """
    out = []
    cursor = 0
    for m in REF_TOKEN.finditer(text):
        out.append(escape_prose(text[cursor:m.start()]))
        label = plan_.label(m.group(1))
        out.append(f"@{label}" if label else "")
        cursor = m.end()
    out.append(escape_prose(text[cursor:]))
    return "".join(out)


def prepared_item(item: Item, plan_: "Plan") -> dict:
    """A JSON view of the item with every prose string prepared."""
    raw = item.model_dump(mode="json")

    def walk(node):
        if isinstance(node, str):
            return prepare(node, plan_)
        if isinstance(node, dict):
            return {k: (v if k in _VERBATIM else walk(v)) for k, v in node.items()}
        if isinstance(node, list):
            return [walk(v) for v in node]
        return node

    raw["slots"] = walk(raw["slots"])
    return raw


# Structural values that are enum keys, not prose: escaping them would break the
# dispatch that reads them.
_VERBATIM = {"kind", "method", "form", "article", "establishes", "setup_form",
             "transition", "ref", "target"}


@dataclass
class Plan:
    """The emission order, with labels resolved by the numbering simulation."""
    events: list[dict] = field(default_factory=list)
    labels: dict[str, str] = field(default_factory=dict)   # item id -> label

    def label(self, item_id: str) -> str | None:
        return self.labels.get(item_id)


def order_key(item: Item, profile: Profile, topics: dict[str, tuple[int, int]]):
    """§I-5 ordering within a topic.

    Explicit `order` first. Then the first *textbook* provenance with a known
    page. A raster capture has no page, so it falls back to its group's
    first-seen position. Board-only items follow, by group and capture index.
    """
    chapter, position = topics.get(item.topic or "", (10_000, 10_000))
    if item.order is not None:
        return (chapter, position, 0, item.order, "", 0.0, item.id)

    for p in item.provenance:
        if p.kind.value == "textbook" and p.page is not None:
            y = p.region[1] if p.region and len(p.region) > 1 else 0.0
            return (chapter, position, 1, profile.sources.rank(p.source), "",
                    float(p.page) * 1e6 + y, item.id)
    for p in item.provenance:
        if p.kind.value == "textbook":
            y = p.region[1] if p.region and len(p.region) > 1 else 0.0
            return (chapter, position, 2, profile.sources.rank(p.source),
                    p.group or "", y, item.id)
    for p in item.provenance:
        y = p.region[1] if p.region and len(p.region) > 1 else 0.0
        return (chapter, position, 3, 0, p.group or "", y, item.id)
    return (chapter, position, 4, 0, "", 0.0, item.id)


def plan(items: list[Item], profile: Profile) -> Plan:
    """Walk chapters and topics, producing the numbering-simulation event list."""
    topics = profile.outline.topic_order()
    ordered = sorted(items, key=lambda it: order_key(it, profile, topics))

    events: list[dict] = []
    by_chapter: dict[int, list[Item]] = {}
    for it in ordered:
        chapter, _ = topics.get(it.topic or "", (10_000, 10_000))
        by_chapter.setdefault(chapter, []).append(it)

    labels: dict[str, str] = {}
    for chapter_index in sorted(by_chapter):
        events.append({"kind": "heading", "chapter": chapter_index})
        for it in by_chapter[chapter_index]:
            entry = profile.taxonomy.entry(it.type.value)
            events.append({"kind": "item", "key": entry.render,
                           "numbered": entry.numbered, "id": it.id})

    for ev in simulate(events):
        if ev["kind"] == "item" and ev.get("label"):
            labels[ev["id"]] = ev["label"]
    return Plan(events=events, labels=labels)


def render_item(item: Item, plan_: Plan, doc: frames.Doc, profile: Profile) -> str:
    entry = profile.taxonomy.entry(item.type.value)
    raw = prepared_item(item, plan_)
    parts = [frames.body_of(raw, doc)]
    for proof in raw["slots"].get("proofs") or []:
        parts.append(f"#proof[{frames.render_proof(proof, doc, parent=raw)}]")

    args = []
    if item.title:
        # A content block, as the WP0.2 torture fixture emits: a title carrying a
        # quote or a backslash cannot then close the literal it sits in.
        args.append(f"title: [{escape(item.title)}]")
    if item.starred:
        args.append("star: true")
    head = (f"#{entry.render}({', '.join(args)})[{parts[0]}]" if args
            else f"#{entry.render}[{parts[0]}]")
    # No `<label>` is written here. `math-item` in the template attaches the
    # label itself, from the same key-and-counter scheme numbering_sim models;
    # writing one as well makes the label occur twice and fails the compile.
    return "\n\n".join([head, *parts[1:]])


def emit(items: list[Item], profile: Profile, title: str,
         symbols_file: str = "symbols-gen.typ") -> str:
    """The whole document. Only `active` items are rendered."""
    renderable = [i for i in items if i.status is Status.ACTIVE]
    plan_ = plan(renderable, profile)
    # The A20 membership view is built from prepared items too, so a citation
    # form pulled out of another item arrives escaped exactly like its own text.
    doc = frames.Doc({i.id: prepared_item(i, plan_) for i in renderable},
                     {i.id for i in renderable})
    by_id = {i.id: i for i in renderable}
    chapters = profile.outline.chapters

    lines = [
        '#import "template-star.typ": *',
        f'#import "{symbols_file}": *',
        "",
        f"#show: project.with(title: [{escape(title)}], date: none)",
        "",
    ]
    for ev in plan_.events:
        if ev["kind"] == "heading":
            index = ev["chapter"]
            if index < len(chapters):
                lines.append(f"= {escape(chapters[index].title)}")
            else:
                # Items whose topic is not in the outline still have to be
                # reachable; dropping them would hide content, which is worse
                # than an untidy final chapter.
                lines.append("= Unplaced")
            lines.append("")
        else:
            lines.append(render_item(by_id[ev["id"]], plan_, doc, profile))
            lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def emit_symbols(profile: Profile) -> str:
    """`symbols-gen.typ` — the `#let` bindings from the field profile (§I-5)."""
    lines = ["// GENERATED — do not hand-edit. Rebuild with `knowledge-base build`.",
             "// Bindings come from fields/<field>/profile/symbols.yaml."]
    for binding in profile.bindings.bindings:
        if binding.note:
            lines.append(f"// {binding.note}")
        lines.append(f"#let {binding.name} = {binding.value}")
    return "\n".join(lines) + "\n"


def write(items: list[Item], profile: Profile, title: str, out_dir: Path,
          template: Path) -> dict[str, Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    main = out_dir / "main.typ"
    symbols = out_dir / "symbols-gen.typ"
    main.write_text(emit(items, profile, title), encoding="utf-8", newline="")
    symbols.write_text(emit_symbols(profile), encoding="utf-8", newline="")
    target = out_dir / template.name
    if target.resolve() != template.resolve():
        target.write_bytes(template.read_bytes())
    log.info("emitted %d items -> %s", len(items), main)
    return {"main": main, "symbols": symbols, "template": target}
