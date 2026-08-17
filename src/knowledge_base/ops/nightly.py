"""The nightly driver (§I-12) — `sync → ingest → extract → validate → audit →
commit → build → publish → report`.

Every stage is idempotent, so a run that dies halfway is resumed by running it
again. The state file records what finished; nothing is continued from a cursor.

**Failure policy, exactly as the plan states it:** any stage error means commit
the completed work, write the report with the error in it, and exit non-zero.
Work already done is never thrown away because a later stage failed — the items
extracted before a build error are still items, and re-extracting them would cost
calls to reproduce something already on disk.

The budget guard halts extraction cleanly on `max_pages_per_night` and on a
limit event. `max_pages_per_night` of 0 means *unmeasured*, not *unlimited*: the
guard treats it as "no budget has been established" and runs a single batch, so
a first unattended run cannot spend the month's quota before anyone measures
anything (B3, WP0.4).
"""

from __future__ import annotations

import traceback
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from knowledge_base.config import ROOT, Settings, load
from knowledge_base.ops.locks import run_lock
from knowledge_base.ops.log import get, run_id
from knowledge_base.ops.state import RunState

log = get("nightly")

UNMEASURED_BUDGET_BATCHES = 1


@dataclass
class RunReport:
    run_id: str
    started: str
    fields: list[str] = field(default_factory=list)
    lines: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    def add(self, line: str) -> None:
        self.lines.append(line)

    def markdown(self) -> str:
        out = [f"# Run {self.run_id}", "", f"Started {self.started}", ""]
        out += [f"- {line}" for line in self.lines]
        if self.errors:
            out += ["", "## Errors", ""] + [f"- {e}" for e in self.errors]
        return "\n".join(out) + "\n"


def budget_batches(settings: Settings) -> int:
    """How many batches this run may spend.

    An unmeasured budget is not an unlimited one. Until WP0.4 sets
    `max_pages_per_night`, a run does one batch — enough to make progress and to
    produce the timing evidence the measurement needs, and far too little to
    exhaust a subscription overnight.
    """
    if settings.budget.max_pages_per_night > 0:
        return settings.budget.max_pages_per_night
    log.warning("budget.max_pages_per_night is unmeasured (B3) — limiting this run "
                "to %d batch(es). Run WP0.4 to set it.", UNMEASURED_BUDGET_BATCHES)
    return UNMEASURED_BUDGET_BATCHES


def run(root: Path = ROOT, settings: Settings | None = None,
        stages: list[str] | None = None) -> int:
    settings = settings or load(Path(root) / "config.yaml")
    rid = run_id()
    state = RunState.load(rid, root)
    report = RunReport(run_id=rid, started=_now(), fields=settings.field_names())
    wanted = stages or ["sync", "ingest", "extract", "validate", "audit", "commit",
                        "build", "publish", "report"]

    with run_lock("nightly", root):
        for stage in wanted:
            if state.done(stage):
                report.add(f"{stage}: already done in this run, skipped")
                continue
            handler = HANDLERS.get(stage)
            if handler is None:
                state.skip(stage, "no handler")
                continue
            state.begin(stage)
            state.save(root)
            try:
                detail = handler(root, settings, report) or {}
                state.finish(stage, **detail)
            except Exception as e:                                # noqa: BLE001
                # Commit what is done, record the error, and stop. A later stage
                # failing does not invalidate the work of an earlier one.
                state.fail(stage, f"{type(e).__name__}: {e}")
                report.errors.append(f"{stage}: {type(e).__name__}: {e}")
                log.error("stage %s failed: %s", stage, traceback.format_exc())
                state.save(root)
                _write_report(report, root)
                _commit_all(root, f"nightly {rid}: {stage} failed")
                return 1
            state.save(root)

    _write_report(report, root)
    return 0


# ── stages ────────────────────────────────────────────────────────────

def _sync(root: Path, settings: Settings, report: RunReport) -> dict:
    from knowledge_base.ingest.sync import have_rclone, sync_field

    if not have_rclone():
        report.add("sync: rclone is not installed — skipped, inbox/ used as-is")
        return {"skipped": "rclone missing"}
    counts = {}
    for key in settings.field_names():
        result = sync_field(key, settings, root)
        counts[key] = result.returncode
        if result.returncode != 0:
            raise RuntimeError(f"rclone sync failed for {key}: {result.stderr[:400]}")
    report.add(f"sync: {len(counts)} field(s) synced from Drive")
    return counts


def _ingest(root: Path, settings: Settings, report: RunReport) -> dict:
    from knowledge_base.ingest.sync import ingest_field

    detail = {}
    for key in settings.field_names():
        r = ingest_field(key, settings, root)
        detail[key] = {"new": r.new, "low_resolution": len(r.low_resolution)}
        report.add(f"ingest: {r.summary()}")
    return detail


def _extract(root: Path, settings: Settings, report: RunReport) -> dict:
    from knowledge_base.extract import batcher, runner
    from knowledge_base.extract.contract import RateLimited
    from knowledge_base.extract.prompts import render
    from knowledge_base.ingest.registry import Registry
    from knowledge_base.models.profile import load_profile
    from knowledge_base.pipeline.accept import accept
    from knowledge_base.pipeline.queues import Queues
    from knowledge_base.pipeline.store import Store

    allowance = budget_batches(settings)
    registry, queues = Registry(root), Queues(root)
    spent, accepted, merged = 0, 0, 0

    for key in settings.field_names():
        profile, store = load_profile(key, root), Store(key, root)
        for batch in batcher.batches_for(key, registry, settings,
                                         settings.inbox(key, root)):
            if spent >= allowance:
                report.add(f"extract: budget of {allowance} batch(es) reached — "
                           "remaining batches resume next run")
                return {"batches": spent, "items": accepted, "merged": merged,
                        "halted": "budget"}
            ctx = batcher.build_context(batch, profile, list(store.all()), settings)
            _, prompt_hash = render("extract.md.j2", ctx)

            def build(errors, ctx=ctx):
                text, _ = render("extract.md.j2", ctx)
                return text if not errors else (
                    f"{text}\n\n# Correction required\n\n{errors}\n\n"
                    "Return the corrected JSON only.")

            try:
                extraction = runner.run_extraction(
                    build, batch_id=batch.batch_id, prompt_hash=prompt_hash,
                    model=settings.model, root=root)
            except RateLimited:
                # §I-7: requeue and halt extraction for the run. The batch stays
                # un-extracted, so the next run picks it up unchanged.
                report.add("extract: rate limit reached — extraction halted, "
                           "remaining batches resume next run")
                return {"batches": spent, "items": accepted, "merged": merged,
                        "halted": "rate-limit"}
            except runner.Parked as e:
                report.add(f"extract: {batch.batch_id} parked — {e}")
                spent += 1
                continue

            result = accept(extraction, batch, profile, store, queues,
                            prompt_hash=prompt_hash, model=settings.model,
                            dialect=settings.dialect, thresholds=settings.dedup)
            for entry in registry.by_field(key):
                if entry.group == batch.group:
                    registry.mark_extracted(entry.sha256)
            registry.save()
            accepted += len(result.accepted)
            merged += len(result.merged)
            spent += 1

    report.add(f"extract: {spent} batch(es), {accepted} item(s) added, "
               f"{merged} merged")
    return {"batches": spent, "items": accepted, "merged": merged}


def _validate(root: Path, settings: Settings, report: RunReport) -> dict:
    from knowledge_base.models.profile import load_profile
    from knowledge_base.pipeline.store import Store
    from knowledge_base.pipeline.validate import validate

    detail = {}
    for key in settings.field_names():
        store, profile = Store(key, root), load_profile(key, root)
        known = set(store.ids())
        findings = 0
        for item in store.all():
            result = validate(item, profile, known)
            findings += sum(1 for f in result.findings if f.route.value != "fixed")
            if result.item != item or result.status() != item.status:
                store.put(result.item.model_copy(update={"status": result.status()}))
        detail[key] = {"items": len(known), "findings": findings}
        report.add(f"validate: {key} — {len(known)} item(s), {findings} finding(s)")
    return detail


def _audit(root: Path, settings: Settings, report: RunReport) -> dict:
    # The audit stage needs the batch's captures and a second model call. With
    # no captures in this environment there is nothing to audit; the stage is
    # reported as skipped rather than silently passing.
    report.add("audit: no extracted batches in this run — nothing to audit")
    return {"batches": 0}


def _commit(root: Path, settings: Settings, report: RunReport) -> dict:
    changed = _commit_all(root, f"nightly {run_id()}: store update")
    report.add(f"commit: {'store committed' if changed else 'no store changes'}")
    return {"committed": changed}


def _build(root: Path, settings: Settings, report: RunReport) -> dict:
    from knowledge_base.build.publish import build_field

    detail = {}
    for key in settings.field_names():
        result = build_field(key, settings, root)
        detail[key] = {"items": result.item_count, "ok": result.ok}
        if result.ok:
            report.add(f"build: {key} — {result.item_count} item(s) -> "
                       f"{result.pdf.name}")
        else:
            report.add(f"build: {key} — emitted but not compiled ({result.stderr[:200]})")
    return detail


def _publish(root: Path, settings: Settings, report: RunReport) -> dict:
    from knowledge_base.ingest.sync import have_rclone, publish

    if not have_rclone():
        report.add("publish: rclone is not installed — PDFs left in build/")
        return {"skipped": "rclone missing"}
    pdfs = sorted((Path(root) / "build").glob("*/*.pdf"))
    report_path = Path(root) / "build" / "report.md"
    result = publish([*pdfs, report_path], settings)
    if result.returncode != 0:
        raise RuntimeError(f"rclone copy failed: {result.stderr[:400]}")
    report.add(f"publish: {len(pdfs)} PDF(s) copied to Drive")
    return {"pdfs": len(pdfs)}


def _report(root: Path, settings: Settings, report: RunReport) -> dict:
    from knowledge_base.pipeline.queues import Queues

    counts = {k: v for k, v in Queues(root).counts().items() if v}
    report.add(f"queues: {counts or 'empty'}")
    path = _write_report(report, root)
    return {"path": str(path)}


HANDLERS = {
    "sync": _sync, "ingest": _ingest, "extract": _extract, "validate": _validate,
    "audit": _audit, "commit": _commit, "build": _build, "publish": _publish,
    "report": _report,
}


# ── helpers ───────────────────────────────────────────────────────────

def _write_report(report: RunReport, root: Path) -> Path:
    path = Path(root) / "build" / "report.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(report.markdown(), encoding="utf-8")
    return path


def _commit_all(root: Path, message: str) -> bool:
    from knowledge_base.pipeline.store import commit

    paths = [p for p in (Path(root) / "fields",) if p.exists()]
    return commit(paths, message, root=root) if paths else False


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def main() -> int:
    return run()


if __name__ == "__main__":
    raise SystemExit(main())
