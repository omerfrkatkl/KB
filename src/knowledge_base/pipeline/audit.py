"""The coverage audit (§I-9) — a second call that marks the first one's work.

Two parts, and the second is the one that is easy to skip and must not be:

1. **Gaps** — facts present in the source and absent from the items.
2. **Exclusion violations** — every region the extractor skipped is validated
   against the written policy. A region dropped as `worked-demonstration` that
   actually establishes a qualifying fact is a violation. **Exclusions are
   audited, never trusted**, because an exclusion is invisible downstream: the
   item simply is not there, and nothing else in the pipeline will ever ask why.

Both arrays empty is a pass. Otherwise one targeted re-extraction of the named
regions, then the `audit-gap` queue.

The blind-spot caveat stands (B9): the auditor is the same model as the extractor
and shares its failure modes. `knowledge-base spotcheck` exists because of that —
a weekly sample of items shown against their source region is the only check that
is not the model marking itself.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field

from knowledge_base.extract.contract import Audit
from knowledge_base.ops.log import get
from knowledge_base.pipeline.queues import Queues
from knowledge_base.pipeline.store import Store

log = get("audit")


@dataclass
class AuditReport:
    batch_id: str
    passed: bool
    gaps: int = 0
    violations: int = 0
    re_extract_regions: list[dict] = field(default_factory=list)

    def summary(self) -> str:
        if self.passed:
            return f"{self.batch_id}: audit passed"
        return (f"{self.batch_id}: {self.gaps} gap(s), {self.violations} exclusion "
                f"violation(s) — {len(self.re_extract_regions)} region(s) to re-extract")


def handle(audit: Audit, batch_id: str, queues: Queues,
           already_retried: bool = False) -> AuditReport:
    report = AuditReport(batch_id=batch_id, passed=audit.passed,
                         gaps=len(audit.gaps), violations=len(audit.exclusion_violations))
    if audit.passed:
        return report

    regions = [{"capture_id": g.capture_id, "region": g.region,
                "description": g.description, "kind": "gap"} for g in audit.gaps]
    regions += [{"capture_id": v.capture_id, "region": v.region,
                 "description": v.reason, "kind": "exclusion-violation"}
                for v in audit.exclusion_violations]

    if already_retried:
        # One targeted re-extraction, then a human. Looping would spend calls on
        # the same blind spot the auditor already failed to see past.
        for r in regions:
            queues.add("audit-gap", {"batch": batch_id, **r,
                                     "why": "still reported after one targeted "
                                            "re-extraction"})
    else:
        report.re_extract_regions = regions
    return report


def spotcheck(store: Store, count: int = 5, seed: int | None = None) -> list[dict]:
    """A random sample of items with the source region each came from (§I-9).

    This is the one verification the model is not part of. It is sampled rather
    than exhaustive because exhaustive review is what the pipeline exists to
    avoid; the point is to detect a systematic failure, not to catch every item.
    """
    items = [i for i in store.all() if i.provenance]
    if not items:
        return []
    rng = random.Random(seed)
    sample = rng.sample(items, min(count, len(items)))
    out = []
    for item in sample:
        p = item.provenance[0]
        out.append({
            "id": item.id, "type": item.type.value, "title": item.title,
            "statement": (item.slots.get("conclusion") or item.slots.get("body")
                          or item.slots.get("term") or "")[:300],
            "source": p.source, "page": p.page, "locator": p.locator,
            "region": p.region, "capture": p.capture.value,
            "prompt_hash": p.extractor.prompt_hash if p.extractor else None,
        })
    return out
