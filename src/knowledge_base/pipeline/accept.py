"""Acceptance — an extraction becomes stored items (§I-7, §I-8).

The order here matters and follows the plan:

1. `tmp_id`s are mapped to fresh ULIDs **on acceptance**, not before. An id that
   reached the store and then failed validation would leave a hole in a sequence
   that is supposed to be dense and creation-ordered.
2. Every item carries the extractor's provenance — prompt hash, model, dialect —
   so any future quality question traces to the exact prompt that produced it
   (§I-1). Prompt changes never trigger automatic re-extraction.
3. Validation routes each finding. Nothing is force-fitted: an unclassifiable
   region goes to a queue with its transcription intact, because a forced fit is
   silent distortion and undetectable downstream.

Coverage is recorded but not judged here. Judging it is the audit stage's job
(§I-9), and it is a separate model call precisely so that the extractor does not
mark its own work.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from knowledge_base.config import Dedup as Thresholds
from knowledge_base.extract.batcher import Batch
from knowledge_base.extract.contract import Extraction
from knowledge_base.models.item import Extractor, Item, ItemType, Provenance, make
from knowledge_base.models.profile import Profile
from knowledge_base.ops.log import get
from knowledge_base.pipeline import dedup
from knowledge_base.pipeline.queues import Queues
from knowledge_base.pipeline.store import Store
from knowledge_base.pipeline.validate import Route, validate

log = get("accept")


@dataclass
class Acceptance:
    accepted: list[Item] = field(default_factory=list)
    rejected: list[tuple[str, str]] = field(default_factory=list)   # (tmp_id, why)
    merged: list[tuple[str, str, str]] = field(default_factory=list)  # tmp, ulid, how
    queued: dict[str, int] = field(default_factory=dict)
    tmp_to_ulid: dict[str, str] = field(default_factory=dict)

    def note(self, queue: str) -> None:
        self.queued[queue] = self.queued.get(queue, 0) + 1


def accept(extraction: Extraction, batch: Batch, profile: Profile, store: Store,
           queues: Queues, *, prompt_hash: str, model: str | None = None,
           dialect: str = "typst", cli_version: str | None = None,
           thresholds: Thresholds | None = None,
           root: Path | None = None) -> Acceptance:
    result = Acceptance()
    thresholds = thresholds or Thresholds()
    known = set(store.ids())
    extractor = Extractor(cli_version=cli_version, model=model,
                          prompt_hash=prompt_hash, dialect=dialect)
    capture_by_id = {c.id: c for c in batch.captures}

    # A duplicate proposal is a proposal. Dedup decides (§I-4); this only stops
    # the item being created twice under two ids in the same batch.
    proposed_duplicates = {d.tmp_id_or_new: d.of for d in extraction.duplicates}

    for raw in extraction.items:
        if not profile.taxonomy.allows(raw.type):
            queues.add("unclassified", {
                "batch": batch.batch_id, "tmp_id": raw.tmp_id, "type": raw.type,
                "slots": raw.slots,
                "why": f"type {raw.type!r} is not in this field's taxonomy; the "
                       "taxonomy is the emitter allowlist and is never widened "
                       "to fit an item"})
            result.rejected.append((raw.tmp_id, f"type {raw.type} not in taxonomy"))
            result.note("unclassified")
            continue

        provenance = [_provenance(raw, batch, capture_by_id, extractor)]
        try:
            item = make(field=profile.field, type=ItemType(raw.type), slots=raw.slots,
                        title=raw.title, topic=raw.topic, terms_used=raw.terms,
                        provenance=provenance)
        except Exception as e:                                   # noqa: BLE001
            # A shape the schema refuses is never coerced into one it accepts.
            queues.add("unclassified", {
                "batch": batch.batch_id, "tmp_id": raw.tmp_id, "type": raw.type,
                "slots": raw.slots, "why": f"slots do not match the {raw.type} "
                                           f"schema: {e}"})
            result.rejected.append((raw.tmp_id, str(e)))
            result.note("unclassified")
            continue

        validated = validate(item, profile, known)
        item = validated.item.model_copy(update={"status": validated.status()})

        for finding in validated.findings:
            if finding.route is Route.NEW_TERM or (
                    finding.route is Route.FLAG and finding.check == "lexicon.unknown-term"):
                queues.add("new-term", {
                    "field": profile.field, "term": finding.detail.get("term"),
                    "load_bearing": finding.detail.get("load_bearing"),
                    "item": item.id, "batch": batch.batch_id})
                result.note("new-term")
            elif finding.route is Route.PENDING_REF:
                queues.add("pending-ref", {
                    "field": profile.field, "item": item.id,
                    "ref": finding.detail.get("ref"), "where": finding.slot})
                result.note("pending-ref")
            elif finding.route is Route.FLAG:
                queues.add("unclassified", {
                    "field": profile.field, "item": item.id,
                    "check": finding.check, "message": finding.message})
                result.note("unclassified")

        # §I-4. The extractor proposes; this decides. A merge appends
        # provenance and keeps the existing slots — the first capture is the one
        # that was reviewed, and a later one is evidence about where the fact
        # appeared, not a better wording of it.
        decision = dedup.find(item, list(store.all()), profile.lexicon, thresholds,
                              proposed_of=proposed_duplicates.get(raw.tmp_id))
        if decision.merged:
            merged = dedup.merge(decision.target, item)
            store.put(merged)
            result.merged.append((raw.tmp_id, merged.id, decision.outcome.value))
            result.tmp_to_ulid[raw.tmp_id] = merged.id
            continue
        if decision.outcome is dedup.Outcome.QUEUED:
            queues.add("near-duplicate", {
                "field": profile.field, "new_item": item.id,
                "existing_item": decision.target.id if decision.target else None,
                "score": round(decision.score, 3), "why": decision.why})
            result.note("near-duplicate")

        store.put(item)
        known.add(item.id)
        result.accepted.append(item)
        result.tmp_to_ulid[raw.tmp_id] = item.id

    for u in extraction.unclassified:
        # The transcription is kept verbatim. Losing it would mean going back to
        # the pixels, and the whole point of the queue is that nothing is lost.
        queues.add("unclassified", {
            "batch": batch.batch_id, "capture_id": u.capture_id, "region": u.region,
            "transcription": u.transcription, "note": u.note,
            "why": "the extractor could not classify this region and did not force it"})
        result.note("unclassified")

    for p in extraction.pending_refs:
        queues.add("pending-ref", {
            "field": profile.field, "batch": batch.batch_id,
            "item": result.tmp_to_ulid.get(p.tmp_id, p.tmp_id),
            "identifier": p.identifier,
            "why": "an explicit citation whose target is not in the store yet"})
        result.note("pending-ref")

    for f in extraction.figures:
        queues.add("figure-crop", {
            "field": profile.field, "batch": batch.batch_id,
            "parent": result.tmp_to_ulid.get(f.parent, f.parent),
            "capture_id": f.capture_id, "bbox": f.bbox})
        result.note("figure-crop")

    log.info("batch %s: %d accepted, %d merged, %d rejected, queued %s",
             batch.batch_id, len(result.accepted), len(result.merged),
             len(result.rejected), result.queued)
    return result


def _provenance(raw, batch: Batch, capture_by_id, extractor: Extractor) -> dict:
    capture_id = raw.slots.pop("capture_id", None) if isinstance(raw.slots, dict) else None
    capture = capture_by_id.get(capture_id) if capture_id else (
        batch.captures[0] if batch.captures else None)
    return Provenance(
        source=batch.source_key, kind=batch.kind, capture=batch.capture,
        group=batch.group, capture_id=capture.id if capture else None,
        extractor=extractor,
    ).model_dump()
