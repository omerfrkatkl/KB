"""Deduplication (§I-4).

The same page captured on two devices yields different bytes and different
names, so file-hash dedup never catches it. Item-level dedup does, and that is
the expected path, not a failure.

Five outcomes, in the order they are tried:

  exact canonical hash        -> auto-merge
  proposal + ratio >= auto_confirm -> auto-merge
  subset match                -> auto-merge (a review repeat restating a fuller item)
  ratio in [queue_floor, auto_confirm) -> near-duplicate queue
  below queue_floor, unproposed        -> a distinct item

A merge **appends provenance and unions terms and figures, keeping the existing
slots**. It never rewrites content. That asymmetry is deliberate: the first
capture of a fact is the one that was reviewed, and a later capture of the same
fact is evidence about *where* it appeared, not a better wording of it.

Thresholds start conservative and are tuned in WP2.4 against a real second
source (B6). Tuning them from constructed pairs would be tuning to the fixture.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from rapidfuzz import fuzz

from knowledge_base.config import Dedup as Thresholds
from knowledge_base.models.item import Item, now
from knowledge_base.models.profile import Lexicon
from knowledge_base.ops.log import get
from knowledge_base.pipeline.canonical import canonical_hash, normalised_statement

log = get("dedup")


class Outcome(StrEnum):
    DISTINCT = "distinct"
    MERGED_EXACT = "merged-exact"
    MERGED_PROPOSED = "merged-proposed"
    MERGED_SUBSET = "merged-subset"
    QUEUED = "near-duplicate-queued"


@dataclass
class Decision:
    outcome: Outcome
    target: Item | None = None      # the surviving item, when merged
    score: float = 0.0
    why: str = ""

    @property
    def merged(self) -> bool:
        return self.outcome in (Outcome.MERGED_EXACT, Outcome.MERGED_PROPOSED,
                                Outcome.MERGED_SUBSET)


def similarity(a: str, b: str) -> float:
    """RapidFuzz token-set ratio on normalised statements, as 0..1."""
    return fuzz.token_set_ratio(a, b) / 100.0


MIN_SUBSET_TOKENS = 5


def contained(incoming: str, existing: str) -> bool:
    """Is `incoming` a restatement of part of `existing`? (§I-4 subset match.)

    Substring containment alone is too weak: the normalised statement
    concatenates conclusion and hypotheses, so a review repeat's hypotheses sit
    after the fuller item's extra conclusion words and the two never line up as
    a contiguous run. Token containment is the faithful reading of "restatement
    of a fuller item" — every word of the shorter statement occurs in the longer
    one, and the longer one says strictly more.

    The token floor keeps two short statements from matching by accident; below
    it, near-duplicate review decides.
    """
    if not incoming or incoming == existing:
        return False
    if incoming in existing:
        return True
    a, b = set(incoming.split()), set(existing.split())
    return len(a) >= MIN_SUBSET_TOKENS and a < b


def merge(existing: Item, incoming: Item) -> Item:
    """Append provenance, union terms and figures, keep the existing slots."""
    provenance = list(existing.provenance)
    seen = {(p.source, p.capture_id, p.image_sha256, p.page, p.locator)
            for p in provenance}
    for p in incoming.provenance:
        key = (p.source, p.capture_id, p.image_sha256, p.page, p.locator)
        if key not in seen:
            provenance.append(p)
            seen.add(key)

    terms = sorted(set(existing.terms_used) | set(incoming.terms_used))
    figures = list(existing.figures)
    known = {f.asset for f in figures}
    figures += [f for f in incoming.figures if f.asset not in known]

    return existing.model_copy(update={
        "provenance": provenance, "terms_used": terms, "figures": figures,
        "refs": sorted(set(existing.refs) | set(incoming.refs)),
        "updated": now(),
    })


def merge_proof(existing: Item, incoming: Item) -> Item:
    """The keep-both-proofs option of the near-duplicate queue (§I-4).

    A second source's proof of the same result is new content, so this is the one
    merge that adds to slots — and it only ever appends to `proofs[]`.
    """
    proofs = list(existing.slots.get("proofs") or [])
    proofs += list(incoming.slots.get("proofs") or [])
    merged = merge(existing, incoming)
    slots = dict(merged.slots)
    slots["proofs"] = proofs
    return merged.model_copy(update={"slots": slots})


def find(incoming: Item, existing: list[Item], lexicon: Lexicon,
         thresholds: Thresholds, proposed_of: str | None = None) -> Decision:
    """Decide what happens to `incoming` against the field's existing items."""
    candidates = [i for i in existing if i.id != incoming.id and i.type is incoming.type]
    if not candidates:
        if proposed_of:
            # The proposal names something this field does not hold — a stale id,
            # or a target of another type. Queue it rather than dropping it: a
            # discarded proposal is the one signal nothing downstream can recover.
            return Decision(Outcome.QUEUED, score=0.0,
                            why=f"proposed as a duplicate of {proposed_of}, which is "
                                "not in the store as an item of this type")
        return Decision(Outcome.DISTINCT, why="no items of this type yet")

    incoming_hash = canonical_hash(incoming, lexicon)
    for item in candidates:
        if canonical_hash(item, lexicon) == incoming_hash:
            return Decision(Outcome.MERGED_EXACT, target=item, score=1.0,
                            why="identical canonical form")

    incoming_text = normalised_statement(incoming, lexicon)
    scored = sorted(
        ((similarity(incoming_text, normalised_statement(i, lexicon)), i)
         for i in candidates), key=lambda pair: -pair[0])
    best_score, best = scored[0]

    if proposed_of:
        target = next((i for i in candidates if i.id == proposed_of), None)
        if target is None:
            return Decision(Outcome.QUEUED, score=best_score,
                            why=f"proposed as a duplicate of {proposed_of}, which is "
                                "not in the store as an item of this type")
        if target is not None:
            score = similarity(incoming_text, normalised_statement(target, lexicon))
            if score >= thresholds.auto_confirm:
                return Decision(Outcome.MERGED_PROPOSED, target=target, score=score,
                                why="the extractor proposed it and the statements agree")
            return Decision(Outcome.QUEUED, target=target, score=score,
                            why="proposed as a duplicate but below auto_confirm")

    # Subset match: a review repeat restates a fuller item's statement.
    for item in candidates:
        text = normalised_statement(item, lexicon)
        if contained(incoming_text, text):
            return Decision(Outcome.MERGED_SUBSET, target=item,
                            score=similarity(incoming_text, text),
                            why="the new statement is contained in an existing one")

    if best_score >= thresholds.auto_confirm:
        return Decision(Outcome.QUEUED, target=best, score=best_score,
                        why="very close, but unproposed — a high score alone never "
                            "merges, because two theorems can differ in one symbol")
    if best_score >= thresholds.queue_floor:
        return Decision(Outcome.QUEUED, target=best, score=best_score,
                        why="near-duplicate")
    return Decision(Outcome.DISTINCT, score=best_score, why="below the queue floor")
