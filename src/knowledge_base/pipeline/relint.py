"""Retroactive lexicon enforcement — `knowledge-base relint` (§I-5).

This is what makes terminological consistency hold *across time* rather than only
forward. A ruling made in year three applies to the items stored in year one, or
the corpus is consistent only in patches.

Two routes, and the split is the safety property:

* **auto** — a word-boundary match in a prose run, outside math, with no casing
  conflict. Substituted and committed with the ruling in the message.
* **ambiguous** — a hit inside math, or a casing conflict. Queued to
  `relint-ambiguous` for a human. Rewriting inside an expression can change what
  it means, and no amount of care in a regex makes that safe.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

from knowledge_base.models.item import Item, now
from knowledge_base.models.profile import Lexicon
from knowledge_base.ops.log import get
from knowledge_base.pipeline.queues import Queues
from knowledge_base.pipeline.store import Store
from knowledge_base.pipeline.validate import MATH_RUN, apply_lexicon, slot_texts

log = get("relint")


@dataclass
class RelintReport:
    ruling: str
    changed: list[str] = field(default_factory=list)
    ambiguous: list[tuple[str, str, str]] = field(default_factory=list)
    substitutions: int = 0

    def summary(self) -> str:
        return (f"relint {self.ruling}: {len(self.changed)} items rewritten "
                f"({self.substitutions} substitutions), "
                f"{len(self.ambiguous)} queued as ambiguous")


def math_hits(text: str, variant: str) -> bool:
    pattern = re.compile(_boundary(variant), re.IGNORECASE)
    return any(pattern.search(run) for run in MATH_RUN.findall(text))


def casing_conflict(text: str, variant: str) -> bool:
    """The variant appears in a casing the substitution cannot preserve — mixed
    or internal capitals, where a first-letter rule would guess wrong."""
    for hit in re.findall(_boundary(variant), text, re.IGNORECASE):
        if hit != variant and hit != variant.capitalize() and hit != variant.upper():
            return True
    return False


def _boundary(term: str) -> str:
    escaped = re.escape(term)
    left = r"\b" if term[:1].isalnum() else ""
    right = r"\b" if term[-1:].isalnum() else ""
    return f"{left}{escaped}{right}"


def relint(store: Store, lexicon: Lexicon, queues: Queues,
           ruling: str = "lexicon", apply: bool = True) -> RelintReport:
    report = RelintReport(ruling=ruling)
    for item in list(store.all()):
        changed: dict[str, str] = {}
        for slot, text in slot_texts(item):
            for variant in lexicon.banned:
                if not re.search(_boundary(variant), text, re.IGNORECASE):
                    continue
                if math_hits(text, variant) or casing_conflict(text, variant):
                    report.ambiguous.append((item.id, slot, variant))
                    queues.add("relint-ambiguous", {
                        "item": item.id, "slot": slot, "variant": variant,
                        "canonical": lexicon.banned[variant], "text": text,
                        "why": "the hit is inside math or in a casing the automatic "
                               "substitution cannot preserve"})
            new, applied = apply_lexicon(text, lexicon.banned)
            if new != text:
                changed[slot] = new
                report.substitutions += len(applied)

        if changed and apply:
            from knowledge_base.pipeline.validate import _apply

            store.put(item.model_copy(update={"slots": _apply(item.slots, changed),
                                              "updated": now()}))
        if changed:
            report.changed.append(item.id)

    log.info("%s", report.summary())
    return report


def commit_relint(store: Store, report: RelintReport, root: Path) -> bool:
    from knowledge_base.pipeline.store import commit

    paths = [store.path(i) for i in report.changed]
    return commit(paths, f"relint: {report.ruling}", root=root)


def rule_in(item: Item, variant: str) -> bool:
    return any(re.search(_boundary(variant), text, re.IGNORECASE)
               for _, text in slot_texts(item))
