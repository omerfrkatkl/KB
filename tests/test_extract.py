"""WP1.3 — batching, the context pack, the inner contract, the runner, acceptance.

Everything here runs offline. Nothing in this file calls a model: the runner is
exercised through `KB_REPLAY=1` against recorded envelopes, which is exactly how
the plan intends every post-extraction stage to be tested. **No claim in this
file is evidence about extraction quality** — that needs real captures and is
WP0.3.
"""

import json
import os
from pathlib import Path

import make_captures as mk
import pytest

from knowledge_base import config
from knowledge_base.extract import batcher, contract, runner
from knowledge_base.extract.contract import ContractError, RateLimited
from knowledge_base.extract.prompts import render
from knowledge_base.ingest.registry import Registry
from knowledge_base.ingest.sync import ingest_field
from knowledge_base.models import item as M
from knowledge_base.models.profile import load_profile
from knowledge_base.pipeline.accept import accept
from knowledge_base.pipeline.queues import Queues
from knowledge_base.pipeline.store import Store

ROOT = Path(__file__).resolve().parents[1]
FIELD = "complex-analysis"


@pytest.fixture(scope="module")
def profile():
    return load_profile(FIELD, ROOT)


@pytest.fixture(scope="module")
def settings():
    return config.load(ROOT / "config.yaml")


@pytest.fixture
def inbox(tmp_path):
    d = tmp_path / "inbox" / FIELD
    (d / "Lecture-Boards").mkdir(parents=True)
    (d / "Texts" / "Brown & Churchill 9e").mkdir(parents=True)
    return d


GOOD = {
    "batch_id": "b1",
    "items": [{"tmp_id": "tmp-1", "type": "definition",
               "slots": {"term": "domain", "form": "noun", "article": "a",
                         "body": "a non-empty open connected set"},
               "topic": "basics", "terms": ["domain"]}],
    "fragments": [], "duplicates": [], "unclassified": [], "pending_refs": [],
    "figures": [], "coverage": [{"capture_id": "c1", "region": [0, 0, 10, 10],
                                 "disposition": "items:tmp-1"}],
    "terms": ["domain"], "notes": None,
}


# ── the inner contract ────────────────────────────────────────────────

def test_contract_parses_the_documented_shape():
    e = contract.parse_extraction(json.dumps(GOOD))
    assert e.items[0].tmp_id == "tmp-1"
    assert e.coverage[0].items() == ["tmp-1"]


def test_json_is_cut_from_the_first_brace_to_the_last():
    wrapped = "Here is the batch:\n```json\n" + json.dumps(GOOD) + "\n```\nDone."
    assert contract.parse_extraction(wrapped).batch_id == "b1"


def test_prose_only_response_fails_the_call():
    with pytest.raises(ContractError):
        contract.parse_extraction("I was unable to read the images.")


def test_an_unknown_field_fails_rather_than_being_ignored():
    """A silently dropped field would produce plausible wrong output for a batch."""
    payload = dict(GOOD, unexpected="value")
    with pytest.raises(ContractError):
        contract.parse_extraction(json.dumps(payload))


def test_coverage_dispositions_are_readable():
    c = contract.Coverage(capture_id="c1", disposition="items:tmp-1,tmp-2")
    assert c.items() == ["tmp-1", "tmp-2"]
    x = contract.Coverage(capture_id="c1", disposition="excluded:foreign-subject")
    assert x.reason() == "foreign-subject" and x.items() == []


def test_audit_contract_and_its_pass_condition():
    a = contract.parse_audit('{"gaps": [], "exclusion_violations": []}')
    assert a.passed
    b = contract.parse_audit(
        '{"gaps": [{"capture_id": "c1", "description": "a definition was missed"}],'
        ' "exclusion_violations": []}')
    assert not b.passed


# ── the CLI envelope (B2 — shape unverified against the live CLI) ──────

def test_envelope_text_from_the_documented_field():
    assert contract.envelope_text(json.dumps({"result": "{}"})) == "{}"


def test_envelope_text_from_a_content_list():
    raw = json.dumps({"content": [{"text": "{\"a\": 1}"}]})
    assert contract.envelope_text(raw) == '{"a": 1}'


def test_a_bare_non_json_response_is_still_parsed():
    raw = "Here is the batch: " + json.dumps(GOOD)
    assert contract.envelope_text(raw) == raw
    assert contract.parse_extraction(contract.envelope_text(raw)).batch_id == "b1"


def test_an_unwrapped_contract_is_recognised():
    """`--bare` may hand back the contract itself with no envelope around it."""
    raw = json.dumps(GOOD)
    assert contract.envelope_text(raw) == raw


def test_rate_limit_signatures_raise_rather_than_parse():
    for text in ('{"result": "usage limit reached"}', "Error: rate limit exceeded",
                 '{"is_error": true, "result": "too many requests"}'):
        with pytest.raises(RateLimited):
            contract.envelope_text(text)


def test_an_unrecognised_envelope_names_the_uncertainty():
    with pytest.raises(ContractError) as e:
        contract.envelope_text(json.dumps({"unknown_shape": True}))
    assert "B2" in str(e.value)


# ── batching (§I-7) ───────────────────────────────────────────────────

def test_batches_respect_the_configured_sizes(tmp_path, inbox, settings):
    d = inbox / "Texts" / "Brown & Churchill 9e"
    for i in range(15):
        mk.make_screenshot(d / f"s{i:02d}.png", text_height_px=20 + i)
    ingest_field(FIELD, settings, tmp_path)
    reg = Registry(tmp_path)
    out = batcher.batches_for(FIELD, reg, settings, inbox)
    assert [b.size() for b in out] == [6, 6, 3], "raster_captures = 6"
    assert len({b.batch_id for b in out}) == 3


def test_low_resolution_captures_are_not_batched(tmp_path, inbox, settings):
    d = inbox / "Texts" / "Brown & Churchill 9e"
    mk.make_screenshot(d / "ok.png", text_height_px=40)
    mk.make_screenshot(d / "blurry.png", text_height_px=6)
    measured = settings.model_copy(update={"resolution_floor_px": 20})
    ingest_field(FIELD, measured, tmp_path)
    out = batcher.batches_for(FIELD, Registry(tmp_path), measured, inbox)
    assert sum(b.size() for b in out) == 1


def test_already_extracted_captures_are_not_rebatched(tmp_path, inbox, settings):
    mk.make_screenshot(inbox / "Texts" / "Brown & Churchill 9e" / "s.png")
    ingest_field(FIELD, settings, tmp_path)
    reg = Registry(tmp_path)
    digest = reg.by_field(FIELD)[0].sha256
    reg.mark_extracted(digest)
    assert batcher.batches_for(FIELD, reg, settings, inbox) == []


# ── the context pack ──────────────────────────────────────────────────

def batch_for(field=FIELD):
    return batcher.Batch(batch_id="b1", field_key=field, group="g1", kind="textbook",
                         capture="raster", source_key="bc9e",
                         captures=[batcher.Capture(id="c1", path=Path("/x.png"),
                                                   kind="textbook", capture="raster",
                                                   source_key="bc9e")])


def test_context_pack_renders_and_is_deterministic(profile, settings):
    ctx = batcher.build_context(batch_for(), profile, [], settings)
    a, ha = render("extract.md.j2", ctx)
    b, hb = render("extract.md.j2", ctx)
    assert a == b and ha == hb
    assert "{{" not in a and "Undefined" not in a


def test_the_pack_carries_the_compiled_policy(profile, settings):
    ctx = batcher.build_context(batch_for(), profile, [], settings)
    text, _ = render("extract.md.j2", ctx)
    assert "foreign-subject" in text, "the exclusion vocabulary reached the extractor"
    assert "holomorphic" in text, "the compiled lexicon reached the extractor"
    assert "citation_form" in text, "the generated schemas reached the extractor"


def test_open_items_and_the_index_come_from_the_store(profile, settings):
    open_item = M.make(field=FIELD, type="theorem", status="open", slots=dict(
        citation_form="a limit is unique", hypotheses=[], conclusion="$L$ is unique",
        proofs=[dict(method="direct",
                     steps=[dict(claim="$a = b$",
                                 justification=dict(kind="by-computation"))])]))
    ctx = batcher.build_context(batch_for(), profile, [open_item], settings)
    assert ctx["open_items"][0]["id"] == open_item.id
    assert "conclusion" in ctx["open_items"][0]["missing"]
    assert ctx["item_index"][0]["digest"].startswith("$L$")


def test_the_identifier_table_maps_citations_to_ulids(profile, settings):
    item = M.make(field=FIELD, type="theorem",
                  provenance=[dict(source="bc9e", kind="textbook", capture="pdf",
                                   page=12, locator="Theorem 2.4")],
                  slots=dict(citation_form="c", hypotheses=[], conclusion="x", proofs=[]))
    ctx = batcher.build_context(batch_for(), profile, [item], settings)
    assert ctx["identifier_table"] == [
        {"identifier": "Theorem 2.4", "id": item.id, "title": None}]


def test_the_audit_pack_shares_the_extractor_s_exclusion_list(profile, settings):
    e = contract.parse_extraction(json.dumps(GOOD))
    ctx = batcher.build_audit_context(batch_for(), profile, e)
    text, _ = render("audit.md.j2", ctx)
    for key in ("worked-demonstration", "foreign-subject", "source-correction"):
        assert key in text


# ── the runner: record and replay ─────────────────────────────────────

def test_replay_serves_the_recording_and_never_calls(tmp_path, monkeypatch):
    prompt = "the prompt"
    cid = runner.call_id("b1", prompt, 0)
    runner.record(runner.CallRecord(
        call_id=cid, batch_id="b1", kind="extract", prompt_sha256="x",
        prompt_hash="h", started="t", finished="t", returncode=0,
        envelope=json.dumps({"result": json.dumps(GOOD)}), attempt=0), tmp_path)

    monkeypatch.setenv("KB_REPLAY", "1")

    def explode(*a, **kw):
        raise AssertionError("replay must not shell out")

    monkeypatch.setattr(runner.subprocess, "run", explode)
    result = runner.run_extraction(lambda errors: prompt, batch_id="b1",
                                   prompt_hash="h", root=tmp_path)
    assert result.items[0].tmp_id == "tmp-1"


def test_replay_without_a_recording_parks_rather_than_calling(tmp_path, monkeypatch):
    monkeypatch.setenv("KB_REPLAY", "1")
    with pytest.raises(runner.Parked) as e:
        runner.run_extraction(lambda errors: "p", batch_id="missing",
                              prompt_hash="h", root=tmp_path)
    assert "no recording" in str(e.value)


def test_calls_are_recorded_with_their_prompt_hash(tmp_path, monkeypatch):
    monkeypatch.delenv("KB_REPLAY", raising=False)

    class Done:
        returncode = 0
        stdout = json.dumps({"result": json.dumps(GOOD)})
        stderr = ""

    monkeypatch.setattr(runner.subprocess, "run", lambda *a, **kw: Done())
    runner.run_extraction(lambda errors: "p", batch_id="b9", prompt_hash="ph1",
                          root=tmp_path)
    files = list((tmp_path / "state" / "calls").glob("*.json"))
    assert files
    assert json.loads(files[0].read_text())["prompt_hash"] == "ph1"


def test_a_malformed_response_retries_with_the_errors_appended(tmp_path, monkeypatch):
    monkeypatch.delenv("KB_REPLAY", raising=False)
    seen = []

    class Bad:
        returncode = 0
        stdout = json.dumps({"result": "not json at all"})
        stderr = ""

    class Good:
        returncode = 0
        stdout = json.dumps({"result": json.dumps(GOOD)})
        stderr = ""

    responses = [Bad(), Good()]
    monkeypatch.setattr(runner.subprocess, "run",
                        lambda *a, **kw: responses.pop(0))

    def build(errors):
        seen.append(errors)
        return "prompt" + (f"\n\nERRORS:\n{errors}" if errors else "")

    result = runner.run_extraction(build, batch_id="b2", prompt_hash="h", root=tmp_path)
    assert result.batch_id == "b1"
    assert seen[0] is None and seen[1] is not None, "the retry is told what failed"


def test_three_failures_park_the_batch(tmp_path, monkeypatch):
    monkeypatch.delenv("KB_REPLAY", raising=False)

    class Bad:
        returncode = 0
        stdout = json.dumps({"result": "still not json"})
        stderr = ""

    monkeypatch.setattr(runner.subprocess, "run", lambda *a, **kw: Bad())
    with pytest.raises(runner.Parked) as e:
        runner.run_extraction(lambda errors: "p", batch_id="b3", prompt_hash="h",
                              root=tmp_path)
    assert "state/calls/" in str(e.value)


def test_a_rate_limit_halts_extraction(tmp_path, monkeypatch):
    monkeypatch.delenv("KB_REPLAY", raising=False)

    class Limited:
        returncode = 0
        stdout = json.dumps({"result": "usage limit reached, try again later"})
        stderr = ""

    monkeypatch.setattr(runner.subprocess, "run", lambda *a, **kw: Limited())
    with pytest.raises(RateLimited):
        runner.run_extraction(lambda errors: "p", batch_id="b4", prompt_hash="h",
                              root=tmp_path)


def test_a_timeout_is_recorded_and_parks(tmp_path, monkeypatch):
    monkeypatch.delenv("KB_REPLAY", raising=False)

    def timeout(*a, **kw):
        raise runner.subprocess.TimeoutExpired(cmd="claude", timeout=1)

    monkeypatch.setattr(runner.subprocess, "run", timeout)
    with pytest.raises(runner.Parked):
        runner.run_extraction(lambda errors: "p", batch_id="b5", prompt_hash="h",
                              root=tmp_path, model=None)


# ── acceptance (§I-7 -> §I-8) ─────────────────────────────────────────

def test_tmp_ids_become_ulids_only_on_acceptance(tmp_path, profile):
    store, queues = Store(FIELD, tmp_path), Queues(tmp_path)
    e = contract.parse_extraction(json.dumps(GOOD))
    result = accept(e, batch_for(), profile, store, queues, prompt_hash="h")
    assert len(result.accepted) == 1
    ulid = result.tmp_to_ulid["tmp-1"]
    assert store.exists(ulid) and ulid != "tmp-1"


def test_provenance_records_the_prompt_that_produced_the_item(tmp_path, profile):
    store, queues = Store(FIELD, tmp_path), Queues(tmp_path)
    e = contract.parse_extraction(json.dumps(GOOD))
    item = accept(e, batch_for(), profile, store, queues,
                  prompt_hash="abc123", model="m", dialect="typst").accepted[0]
    p = item.provenance[0]
    assert p.extractor.prompt_hash == "abc123" and p.extractor.model == "m"
    assert p.source == "bc9e" and p.kind.value == "textbook"
    assert p.group == "g1"


def test_a_type_outside_the_taxonomy_is_queued_never_coerced(tmp_path, profile):
    store, queues = Store(FIELD, tmp_path), Queues(tmp_path)
    payload = dict(GOOD)
    payload["items"] = [dict(GOOD["items"][0], type="exercise")]
    e = contract.parse_extraction(json.dumps(payload))
    result = accept(e, batch_for(), profile, store, queues, prompt_hash="h")
    assert not result.accepted and result.rejected
    assert queues.counts()["unclassified"] == 1
    assert store.ids() == []


def test_slots_that_fail_their_schema_are_queued_never_trimmed(tmp_path, profile):
    store, queues = Store(FIELD, tmp_path), Queues(tmp_path)
    payload = dict(GOOD)
    payload["items"] = [{"tmp_id": "tmp-9", "type": "theorem",
                         "slots": {"conclusion": "x"}, "terms": []}]
    e = contract.parse_extraction(json.dumps(payload))
    result = accept(e, batch_for(), profile, store, queues, prompt_hash="h")
    assert not result.accepted
    entry = queues.list("unclassified")[0]
    assert entry.payload["slots"] == {"conclusion": "x"}, "the transcription is kept"


def test_unclassified_regions_keep_their_transcription(tmp_path, profile):
    store, queues = Store(FIELD, tmp_path), Queues(tmp_path)
    payload = dict(GOOD)
    payload["unclassified"] = [{"capture_id": "c1", "region": [0, 0, 5, 5],
                                "transcription": "a diagram with three labelled arcs",
                                "note": "not obviously a definition or a result"}]
    e = contract.parse_extraction(json.dumps(payload))
    accept(e, batch_for(), profile, store, queues, prompt_hash="h")
    entries = [q for q in queues.list("unclassified")
               if "transcription" in q.payload]
    assert entries[0].payload["transcription"].startswith("a diagram")


def test_duplicate_proposals_queue_rather_than_merge(tmp_path, profile):
    store, queues = Store(FIELD, tmp_path), Queues(tmp_path)
    payload = dict(GOOD)
    payload["duplicates"] = [{"tmp_id_or_new": "tmp-1", "of": "01J9XA5T7K3M2N8P4Q6R9S0TVA"}]
    e = contract.parse_extraction(json.dumps(payload))
    result = accept(e, batch_for(), profile, store, queues, prompt_hash="h")
    assert len(result.accepted) == 1, "the extractor proposes; dedup decides"
    assert queues.counts()["near-duplicate"] == 1


def test_pending_refs_and_figures_route_to_their_queues(tmp_path, profile):
    store, queues = Store(FIELD, tmp_path), Queues(tmp_path)
    payload = dict(GOOD)
    payload["pending_refs"] = [{"tmp_id": "tmp-1", "identifier": "Theorem 2.4"}]
    payload["figures"] = [{"parent": "tmp-1", "capture_id": "c1",
                           "bbox": [0, 0, 100, 100]}]
    e = contract.parse_extraction(json.dumps(payload))
    accept(e, batch_for(), profile, store, queues, prompt_hash="h")
    counts = queues.counts()
    assert counts["pending-ref"] == 1 and counts["figure-crop"] == 1


def test_an_unknown_term_reaches_the_new_term_queue(tmp_path, profile):
    store, queues = Store(FIELD, tmp_path), Queues(tmp_path)
    payload = dict(GOOD)
    payload["items"] = [dict(GOOD["items"][0], terms=["quasiregular"])]
    e = contract.parse_extraction(json.dumps(payload))
    accept(e, batch_for(), profile, store, queues, prompt_hash="h")
    assert queues.counts()["new-term"] == 1


def test_lexicon_substitution_is_applied_before_storage(tmp_path, profile):
    store, queues = Store(FIELD, tmp_path), Queues(tmp_path)
    payload = dict(GOOD)
    payload["items"] = [dict(GOOD["items"][0],
                             slots={"term": "domain", "form": "noun", "article": "a",
                                    "body": "a set on which $f$ is holomorphic"})]
    e = contract.parse_extraction(json.dumps(payload))
    item = accept(e, batch_for(), profile, store, queues, prompt_hash="h").accepted[0]
    assert "analytic" in item.slots["body"] and "holomorphic" not in item.slots["body"]


def test_replay_environment_is_not_left_set():
    """A stray KB_REPLAY would make a real run silently serve stale envelopes."""
    assert os.environ.get("KB_REPLAY") != "1"
