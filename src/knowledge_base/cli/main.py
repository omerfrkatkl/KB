"""The `knowledge-base` command — the §I-10 surface.

The command name is deliberately unabbreviated. Add a shell alias if the length
annoys you day to day; do not rename the entry point.
"""

from __future__ import annotations

import sys
from pathlib import Path

import typer

from knowledge_base import config

ROOT = Path(__file__).resolve().parents[3]
app = typer.Typer(add_completion=False, help="Personal knowledge-base pipeline.")

# stage -> work package that builds it (docs/implementation-plan.md, Part II).
# Empty: every command in the §I-10 surface is wired. What remains unbuilt is
# not a command but a *measurement* — the Phase-0 spikes — which `status`
# reports as UNMEASURED.
PENDING: dict[str, str] = {}


@app.command()
def bootstrap() -> None:
    """Vendor the pinned typst binary and fonts, verifying sha256."""
    from knowledge_base.ops import bootstrap as bs

    raise typer.Exit(code=bs.main([]))


@app.command()
def rules(check: bool = typer.Option(False, help="fail if generated/ is stale")) -> None:
    """Compile rules/ -> generated/ (same as `make rules`)."""
    from knowledge_base.rules import compile_rules

    raise typer.Exit(code=compile_rules.run(root=ROOT, check=check))


@app.command()
def ingest(field: str = typer.Argument(None, help="field key; omit for all")) -> None:
    """Walk inbox/<field>, route, gate, group and register every new capture."""
    from knowledge_base.ingest.sync import ingest_field

    settings = config.load(ROOT / "config.yaml")
    for key in [field] if field else settings.field_names():
        typer.echo(ingest_field(key, settings, ROOT).summary())


@app.command()
def extract(field: str = typer.Argument(None),
            limit: int = typer.Option(0, help="stop after N batches; 0 = no limit"),
            dry_run: bool = typer.Option(False, help="list batches, call nothing")) -> None:
    """Extract every un-extracted capture group of a field.

    Honours `KB_REPLAY=1`, which serves recorded envelopes instead of calling.
    A rate-limit signature halts extraction for the run rather than retrying
    into the limit; the batch stays un-extracted and resumes next time.
    """
    from knowledge_base.extract import batcher, runner
    from knowledge_base.extract.contract import RateLimited
    from knowledge_base.extract.prompts import render
    from knowledge_base.ingest.registry import Registry
    from knowledge_base.models.profile import load_profile
    from knowledge_base.pipeline.accept import accept
    from knowledge_base.pipeline.queues import Queues
    from knowledge_base.pipeline.store import Store

    settings = config.load(ROOT / "config.yaml")
    registry = Registry(ROOT)
    queues = Queues(ROOT)

    for key in [field] if field else settings.field_names():
        profile = load_profile(key, ROOT)
        store = Store(key, ROOT)
        pending = batcher.batches_for(key, registry, settings,
                                      settings.inbox(key, ROOT))
        if limit:
            pending = pending[:limit]
        if dry_run:
            for b in pending:
                typer.echo(f"{b.batch_id}: {b.size()} captures ({b.kind}/{b.capture})")
            continue

        for b in pending:
            items = list(store.all())
            ctx = batcher.build_context(b, profile, items, settings)

            def build_prompt(errors, ctx=ctx):
                text, _ = render("extract.md.j2", ctx)
                return text if not errors else (
                    f"{text}\n\n# Correction required\n\nThe previous response was "
                    f"rejected:\n\n{errors}\n\nReturn the corrected JSON only.")

            _, prompt_hash = render("extract.md.j2", ctx)
            try:
                extraction = runner.run_extraction(
                    build_prompt, batch_id=b.batch_id, prompt_hash=prompt_hash,
                    model=settings.model, root=ROOT)
            except RateLimited:
                typer.echo("rate limit reached — extraction halted for this run; "
                           "the remaining batches resume next time", err=True)
                raise typer.Exit(code=0) from None
            except runner.Parked as e:
                typer.echo(f"{b.batch_id}: parked — {e}", err=True)
                continue

            result = accept(extraction, b, profile, store, queues,
                            prompt_hash=prompt_hash, model=settings.model,
                            dialect=settings.dialect)
            # Only the group's captures are marked; a batch that parked leaves
            # its captures un-extracted so the next run picks them up again.
            for entry in registry.by_field(key):
                if entry.group == b.group:
                    registry.mark_extracted(entry.sha256)
            registry.save()
            typer.echo(f"{b.batch_id}: {len(result.accepted)} items, "
                       f"queued {result.queued or 'nothing'}")


@app.command()
def validate(field: str = typer.Argument(None)) -> None:
    """Re-validate a field's stored items and report where each finding routes."""
    from knowledge_base.models.profile import load_profile
    from knowledge_base.pipeline.store import Store
    from knowledge_base.pipeline.validate import validate as run_validation

    settings = config.load(ROOT / "config.yaml")
    for key in [field] if field else settings.field_names():
        store = Store(key, ROOT)
        profile = load_profile(key, ROOT)
        known = set(store.ids())
        problems = 0
        for item in store.all():
            for finding in run_validation(item, profile, known).findings:
                if finding.route.value != "fixed":
                    problems += 1
                    typer.echo(f"{item.id} [{finding.route.value}] {finding.message}")
        typer.echo(f"{key}: {len(known)} items, {problems} findings")


@app.command()
def build(field: str = typer.Argument(None)) -> None:
    """Emit and compile a field's book from the store."""
    from knowledge_base.build.publish import build_field

    settings = config.load(ROOT / "config.yaml")
    failed = False
    for key in [field] if field else settings.field_names():
        result = build_field(key, settings, ROOT)
        if result.ok:
            typer.echo(f"{key}: {result.item_count} items -> {result.pdf}")
        else:
            failed = True
            typer.echo(f"{key}: build failed — {result.stderr.strip()[:400]}", err=True)
    raise typer.Exit(code=1 if failed else 0)


@app.command()
def sync(field: str = typer.Argument(None), dry_run: bool = typer.Option(False)) -> None:
    """`rclone sync` each field's Drive capture folder into inbox/ (§I-6.1)."""
    from knowledge_base.ingest.sync import have_rclone, sync_field

    if not have_rclone():
        typer.echo("rclone is not installed — install it and complete the Drive "
                   "OAuth flow; the inbox is otherwise used as it stands", err=True)
        raise typer.Exit(code=2)
    settings = config.load(ROOT / "config.yaml")
    for key in [field] if field else settings.field_names():
        result = sync_field(key, settings, ROOT, dry_run=dry_run)
        typer.echo(f"{key}: rclone exited {result.returncode}")
        if result.returncode != 0:
            typer.echo(result.stderr[:400], err=True)


@app.command()
def run(stage: str = typer.Option(None, help="run one stage instead of all")) -> None:
    """One full pipeline pass (§I-12). Idempotent; safe to re-run after a kill."""
    from knowledge_base.ops.locks import AlreadyRunning
    from knowledge_base.ops.nightly import run as run_nightly

    try:
        code = run_nightly(root=ROOT, stages=[stage] if stage else None)
    except AlreadyRunning as e:
        typer.echo(str(e), err=True)
        raise typer.Exit(code=3) from None
    raise typer.Exit(code=code)


@app.command()
def audit(field: str = typer.Argument(None)) -> None:
    """Report what the audit stage would examine.

    The audit is a second model call over a batch's captures (§I-9). With no
    extracted batches it has nothing to mark, and saying so is better than
    reporting a pass nobody earned.
    """
    from knowledge_base.ingest.registry import Registry

    settings = config.load(ROOT / "config.yaml")
    registry = Registry(ROOT)
    for key in [field] if field else settings.field_names():
        extracted = [e for e in registry.by_field(key) if e.extracted]
        typer.echo(f"{key}: {len(extracted)} extracted capture(s) available to audit")
        if not extracted:
            typer.echo("  nothing to audit — the audit marks an extraction, and none "
                       "has been performed")


@app.command()
def spotcheck(field: str = typer.Argument(None), n: int = typer.Option(5)) -> None:
    """Sample N items and show each against the source region it came from.

    The one verification the model is not part of (B9): the auditor shares the
    extractor's blind spots, so a periodic human sample is the only check that is
    not the model marking its own work.
    """
    from rich.console import Console
    from rich.table import Table

    from knowledge_base.pipeline.audit import spotcheck as sample
    from knowledge_base.pipeline.store import Store

    settings = config.load(ROOT / "config.yaml")
    console = Console()
    for key in [field] if field else settings.field_names():
        rows = sample(Store(key, ROOT), count=n)
        table = Table(title=f"{key}: spotcheck")
        for column in ("id", "type", "statement", "source", "page", "locator"):
            table.add_column(column, overflow="fold")
        for row in rows:
            table.add_row(row["id"], row["type"], row["statement"][:120],
                          row["source"] or "", str(row["page"] or ""),
                          row["locator"] or "")
        console.print(table)


@app.command()
def review(queue: str = typer.Argument(None, help="one queue; omit for all")) -> None:
    """Work the decision queues. Every ruling appends to decisions.log."""
    from knowledge_base.cli.review import interactive, work
    from knowledge_base.pipeline.queues import Queues

    ruled = work(Queues(ROOT), interactive, only=queue, root=ROOT)
    typer.echo(f"{ruled} ruling(s) recorded in decisions.log")


@app.command()
def browse(field: str = typer.Argument(None), item: str = typer.Option(None)) -> None:
    """Read the store: one item in full, or a listing of the field."""
    from rich.console import Console
    from rich.table import Table

    from knowledge_base.pipeline.store import Store

    settings = config.load(ROOT / "config.yaml")
    console = Console()
    for key in [field] if field else settings.field_names():
        store = Store(key, ROOT)
        if item:
            console.print(store.get(item))
            return
        table = Table(title=key)
        for column in ("id", "type", "status", "star", "title", "topic"):
            table.add_column(column)
        for it in store.all():
            table.add_row(it.id, it.type.value, it.status.value,
                          "*" if it.starred else "", it.title or "", it.topic or "")
        console.print(table)


@app.command()
def star(item_id: str, field: str = typer.Option(...),
         off: bool = typer.Option(False, "--off")) -> None:
    """Override the derived exam star (A6). `auto` is restored by neither flag."""
    from knowledge_base.pipeline.store import Store

    store = Store(field, ROOT)
    it = store.get(item_id)
    store.put(it.model_copy(update={"exam_star": not off}))
    typer.echo(f"{item_id}: exam_star = {not off}")


@app.command()
def edit(item_id: str, field: str = typer.Option(...)) -> None:
    """Open an item in $EDITOR, then revalidate and compile-smoke it."""
    import os
    import subprocess

    from knowledge_base.build import compile as C
    from knowledge_base.build import emitter
    from knowledge_base.models.profile import load_profile
    from knowledge_base.pipeline.store import Store
    from knowledge_base.pipeline.validate import validate as run_validation

    store = Store(field, ROOT)
    path = store.path(item_id)
    subprocess.run([os.environ.get("EDITOR", "vi"), str(path)], check=False)

    item = store.get(item_id)                     # re-reads and re-validates shape
    profile = load_profile(field, ROOT)
    result = run_validation(item, profile, set(store.ids()))
    for finding in result.findings:
        typer.echo(f"[{finding.route.value}] {finding.message}")

    if C.available(ROOT):
        plan = emitter.plan([item], profile)
        body = emitter.render_item(item, plan, emitter.frames.Doc({}, set()), profile)
        smoke = C.smoke(body, ROOT / "build" / "_smoke",
                        ROOT / "template" / "template-star.typ", root=ROOT)
        typer.echo("compile smoke: " + ("ok" if smoke.ok else smoke.stderr[:400]))
    store.put(result.item)


@app.command()
def relint(field: str = typer.Argument(None),
           ruling: str = typer.Option("lexicon", help="what to record in the commit"),
           dry_run: bool = typer.Option(False)) -> None:
    """Apply the lexicon retroactively across the whole store (§I-5)."""
    from knowledge_base.models.profile import load_profile
    from knowledge_base.pipeline.queues import Queues
    from knowledge_base.pipeline.relint import commit_relint
    from knowledge_base.pipeline.relint import relint as run_relint
    from knowledge_base.pipeline.store import Store

    settings = config.load(ROOT / "config.yaml")
    for key in [field] if field else settings.field_names():
        store = Store(key, ROOT)
        report = run_relint(store, load_profile(key, ROOT).lexicon, Queues(ROOT),
                            ruling=ruling, apply=not dry_run)
        typer.echo(report.summary())
        if not dry_run and report.changed:
            commit_relint(store, report, ROOT)


@app.command()
def status() -> None:
    """Report what is built, what is vendored, what is measured, and what remains."""
    from knowledge_base.ingest.registry import Registry
    from knowledge_base.models.profile import load_profile
    from knowledge_base.pipeline.queues import Queues
    from knowledge_base.pipeline.store import Store

    settings = config.load(ROOT / "config.yaml")
    typst = ROOT / "tools" / "typst"
    fonts = list((ROOT / "fonts").glob("*")) if (ROOT / "fonts").exists() else []
    typer.echo(f"toolchain : {'vendored' if typst.exists() else 'MISSING — run bootstrap'}")
    typer.echo(f"fonts     : {len(fonts)} vendored")
    for name, measured in settings.measured().items():
        typer.echo(f"measured  : {name} = {'set' if measured else 'UNMEASURED (Phase 0)'}")

    registry = Registry(ROOT)
    for key in settings.field_names():
        profile = load_profile(key, ROOT)
        items = list(Store(key, ROOT).all())
        # Proofless results are legitimate (§I-3) and are tracked, never fixed
        # by invention: they complete later from another source.
        proofless = [i for i in items
                     if i.type.value in ("theorem", "lemma", "proposition", "corollary")
                     and not i.slots.get("proofs")]
        typer.echo(
            f"{key}: {len(items)} items "
            f"({sum(1 for i in items if i.status.value == 'active')} active, "
            f"{sum(1 for i in items if i.status.value == 'open')} open, "
            f"{sum(1 for i in items if i.status.value == 'flagged')} flagged), "
            f"{len(proofless)} without a proof, "
            f"{len(registry.by_field(key))} captures, "
            f"{len(profile.lexicon.banned)} lexicon rulings")

    counts = {k: v for k, v in Queues(ROOT).counts().items() if v}
    typer.echo(f"queues    : {counts or 'empty'}")
    if PENDING:
        typer.echo(f"pending   : {', '.join(sorted(PENDING))}")


def _main() -> int:
    try:
        app()
    except SystemExit as e:
        return int(e.code or 0)
    return 0


if __name__ == "__main__":
    sys.exit(_main())
