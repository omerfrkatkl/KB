"""WP4.1 — the nightly stage machine: idempotency, the lock, budget, failure.

The rclone stages are exercised for their *absence* behaviour only. There is no
Drive in this environment, so `sync` and `publish` are tested to skip cleanly
rather than to work — WP4.2's live behaviour needs a configured remote.
"""

import shutil
from pathlib import Path

import pytest

from knowledge_base import config
from knowledge_base.models import item as M
from knowledge_base.ops import nightly
from knowledge_base.ops.locks import AlreadyRunning, run_lock
from knowledge_base.ops.state import STAGES, RunState
from knowledge_base.pipeline.store import Store

ROOT = Path(__file__).resolve().parents[1]
FIELD = "complex-analysis"


@pytest.fixture
def workspace(tmp_path, monkeypatch):
    for name in ("fields", "template", "generated", "prompts"):
        shutil.copytree(ROOT / name, tmp_path / name)
    shutil.copy(ROOT / "config.yaml", tmp_path / "config.yaml")
    (tmp_path / "tools").mkdir()
    (tmp_path / "tools" / "typst").symlink_to((ROOT / "tools" / "typst").resolve())
    (tmp_path / "fonts").symlink_to((ROOT / "fonts").resolve())
    for key in ("complex-analysis", "ordinary-differential-equations"):
        (tmp_path / "inbox" / key / "Lecture-Boards").mkdir(parents=True)
        (tmp_path / "inbox" / key / "Texts").mkdir(parents=True)
    monkeypatch.setenv("KB_RUN_ID", "testrun")
    return tmp_path


@pytest.fixture
def settings():
    return config.load(ROOT / "config.yaml")


# ── the lock (§I-12) ──────────────────────────────────────────────────

def test_two_runs_cannot_overlap(tmp_path):
    with run_lock("nightly", tmp_path):
        with pytest.raises(AlreadyRunning):
            with run_lock("nightly", tmp_path):
                pass


def test_the_lock_is_released_on_exit(tmp_path):
    with run_lock("nightly", tmp_path):
        pass
    with run_lock("nightly", tmp_path):
        pass


# ── run state ─────────────────────────────────────────────────────────

def test_state_round_trips(tmp_path):
    state = RunState.load("r1", tmp_path)
    state.begin("ingest")
    state.finish("ingest", new=3)
    state.save(tmp_path)
    again = RunState.load("r1", tmp_path)
    assert again.done("ingest") and again.stages["ingest"].detail["new"] == 3


def test_every_stage_of_the_plan_is_declared():
    assert STAGES == ("sync", "ingest", "extract", "validate", "audit", "commit",
                      "build", "publish", "report")
    assert set(nightly.HANDLERS) == set(STAGES)


# ── the budget guard (B3) ─────────────────────────────────────────────

def test_an_unmeasured_budget_is_not_an_unlimited_one(settings):
    assert settings.budget.max_pages_per_night == 0
    assert nightly.budget_batches(settings) == nightly.UNMEASURED_BUDGET_BATCHES


def test_a_measured_budget_is_used_as_given(settings):
    measured = settings.model_copy(update={
        "budget": settings.budget.model_copy(update={"max_pages_per_night": 12})})
    assert nightly.budget_batches(measured) == 12


# ── the stage machine ─────────────────────────────────────────────────

def test_a_full_run_without_captures_completes(workspace, settings):
    assert nightly.run(root=workspace, settings=settings) == 0
    report = (workspace / "build" / "report.md").read_text(encoding="utf-8")
    assert "rclone is not installed" in report
    assert "ingest:" in report and "build:" in report


def test_the_run_is_idempotent(workspace, settings):
    assert nightly.run(root=workspace, settings=settings) == 0
    first = (workspace / "build" / "complex-analysis" / "main.typ").read_text(encoding="utf-8")
    assert nightly.run(root=workspace, settings=settings) == 0
    assert (workspace / "build" / "complex-analysis" / "main.typ").read_text(encoding="utf-8") == first


def test_a_completed_stage_is_not_repeated_on_resume(workspace, settings):
    nightly.run(root=workspace, settings=settings, stages=["ingest"])
    state = RunState.load("testrun", workspace)
    assert state.done("ingest")

    calls = []
    original = nightly.HANDLERS["ingest"]
    nightly.HANDLERS["ingest"] = lambda *a: calls.append(1)
    try:
        nightly.run(root=workspace, settings=settings, stages=["ingest"])
    finally:
        nightly.HANDLERS["ingest"] = original
    assert calls == [], "a stage already done in this run is skipped"


def test_a_failing_stage_commits_what_is_done_and_reports(workspace, settings):
    store = Store(FIELD, workspace)
    store.put(M.make(field=FIELD, type="remark", slots=dict(body="a fact worth keeping")))

    def explode(*a):
        raise RuntimeError("simulated build failure")

    original = nightly.HANDLERS["build"]
    nightly.HANDLERS["build"] = explode
    try:
        code = nightly.run(root=workspace, settings=settings,
                           stages=["ingest", "validate", "build", "report"])
    finally:
        nightly.HANDLERS["build"] = original

    assert code == 1, "a stage error exits non-zero"
    report = (workspace / "build" / "report.md").read_text(encoding="utf-8")
    assert "simulated build failure" in report
    assert "ingest:" in report, "work done before the failure is still reported"
    assert RunState.load("testrun", workspace).failed_stages() == ["build"]
    assert store.ids(), "extracted work is not thrown away because a later stage failed"


def test_the_report_names_the_queues(workspace, settings):
    from knowledge_base.pipeline.queues import Queues

    Queues(workspace).add("new-term", {"term": "quasiregular"})
    nightly.run(root=workspace, settings=settings)
    assert "new-term" in (workspace / "build" / "report.md").read_text(encoding="utf-8")


def test_a_second_run_uses_a_new_run_id(workspace, settings, monkeypatch):
    nightly.run(root=workspace, settings=settings)
    monkeypatch.setenv("KB_RUN_ID", "testrun2")
    nightly.run(root=workspace, settings=settings)
    assert (workspace / "state" / "runs" / "testrun.json").exists()
    assert (workspace / "state" / "runs" / "testrun2.json").exists()


def test_the_nightly_script_is_executable():
    script = ROOT / "bin" / "nightly.sh"
    assert script.exists() and script.stat().st_mode & 0o111
