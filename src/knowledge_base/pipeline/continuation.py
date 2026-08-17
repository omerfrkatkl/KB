"""Continuation (§I-7.3) — a proof that ran across two boards becomes one item.

An item whose structure is started but unfinished is `open`. The open-item set
travels in every prompt for its field, and the extractor returns fragments
naming the item each continues. This module merges a fragment into its parent and
revalidates.

Three rules the plan is explicit about:

* **Matching is by content against the open-item set, never by file adjacency.**
  A drop of captures in arbitrary order produces the same result as the same drop
  in perfect order, and a fragment processed before its parent still merges — the
  machinery is symmetric.
* **A fragment never overwrites.** It fills what is empty and appends to lists.
  Overwriting would let a second, worse reading of the same board silently
  replace a good one.
* **Open items that go quiet are queued, not closed.** An item still open after
  `quiet_after_days` raises `open-gone-quiet`; nothing decides on its own that a
  proof was abandoned.
"""

from __future__ import annotations

import copy
from dataclasses import dataclass, field
from datetime import timedelta

from knowledge_base.models.item import Item, Status, now
from knowledge_base.models.profile import Profile
from knowledge_base.ops.log import get
from knowledge_base.pipeline.queues import Queues
from knowledge_base.pipeline.store import Store
from knowledge_base.pipeline.validate import validate

log = get("continuation")

QUIET_AFTER_DAYS = 21


@dataclass
class MergeReport:
    merged: list[str] = field(default_factory=list)
    unmatched: list[str] = field(default_factory=list)
    still_open: list[str] = field(default_factory=list)
    closed: list[str] = field(default_factory=list)


def open_set(store: Store) -> dict[str, Item]:
    return {i.id: i for i in store.all() if i.status is Status.OPEN}


def merge_fragment(parent: Item, payload: dict) -> Item:
    """Fill empty slots and append to lists. Never replace a filled slot."""
    slots = _fill(copy.deepcopy(parent.slots), payload)
    return parent.model_copy(update={"slots": slots, "updated": now()})


# A fragment's list either *extends* the parent's or *continues* its elements,
# and which one it is depends on the slot. `steps` and `hypotheses` are flat
# sequences, so a fragment carries the ones that come after. `proofs`, `cases`
# and `criteria` are structured blocks, so a fragment carries the missing parts
# of block n — appending there would create a second, half-empty proof rather
# than finishing the first.
EXTEND_SLOTS = {"steps", "hypotheses", "terms_used", "refs"}


def _fill(target, payload, slot: str | None = None):
    if isinstance(target, dict) and isinstance(payload, dict):
        for key, value in payload.items():
            if key not in target or target[key] in (None, "", [], {}):
                target[key] = value
            else:
                target[key] = _fill(target[key], value, key)
        return target
    if isinstance(target, list) and isinstance(payload, list):
        if slot in EXTEND_SLOTS:
            return target + [p for p in payload if p not in target]
        out = list(target)
        for index, element in enumerate(payload):
            if index < len(out) and isinstance(out[index], dict) and isinstance(element, dict):
                out[index] = _fill(out[index], element, slot)
            elif index >= len(out):
                out.append(element)
        return out
    return target


def apply_fragments(fragments, store: Store, profile: Profile,
                    queues: Queues) -> MergeReport:
    report = MergeReport()
    known = set(store.ids())
    openable = open_set(store)

    for fragment in fragments:
        parent = openable.get(fragment.continues) or (
            store.get(fragment.continues) if store.exists(fragment.continues) else None)
        if parent is None:
            # A fragment naming nothing is kept, not dropped: the parent may
            # arrive in a later batch, and the transcription is irreplaceable.
            queues.add("unclassified", {
                "continues": fragment.continues, "payload": fragment.payload,
                "why": "a continuation naming an item this field does not hold; the "
                       "parent may arrive later, so the fragment is kept for review"})
            report.unmatched.append(fragment.continues)
            continue

        merged = merge_fragment(parent, fragment.payload)
        result = validate(merged, profile, known)
        merged = result.item.model_copy(update={"status": result.status()})
        store.put(merged)
        report.merged.append(merged.id)
        (report.still_open if merged.status is Status.OPEN
         else report.closed).append(merged.id)
    return report


def sweep_quiet(store: Store, queues: Queues, days: int = QUIET_AFTER_DAYS) -> list[str]:
    """Queue open items nobody has continued. Never closes one automatically."""
    cutoff = now() - timedelta(days=days)
    quiet = []
    for item in open_set(store).values():
        if item.updated < cutoff:
            queues.add("open-gone-quiet", {
                "item": item.id, "type": item.type.value, "title": item.title,
                "last_updated": item.updated.isoformat(),
                "why": f"open for more than {days} days with no continuation; "
                       "an unfinished structure is never completed by guessing"})
            quiet.append(item.id)
    return quiet
