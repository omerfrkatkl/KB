"""WP2.1-2.3 — canonicalisation, dedup, relint, queues, and the review loop.

Thresholds are NOT tuned here. The plan puts tuning in WP2.4, against a real
second Complex Analysis source, and tuning them against constructed pairs would
be tuning to the fixture. These tests check the *behaviour at* the thresholds,
which is a different and testable thing.
"""

from pathlib import Path

import pytest

from knowledge_base.config import Dedup as Thresholds
from knowledge_base.models import item as M
from knowledge_base.models.profile import Lexicon, load_profile
from knowledge_base.pipeline import dedup
from knowledge_base.pipeline.canonical import (
    canonical_hash,
    canonical_text,
    normalise_math,
    normalised_statement,
)
from knowledge_base.pipeline.queues import Queues
from knowledge_base.pipeline.relint import relint
from knowledge_base.pipeline.store import Store

ROOT = Path(__file__).resolve().parents[1]
FIELD = "complex-analysis"
LEX = Lexicon(canonical=[{"term": "analytic"}],
              banned={"holomorphic": "analytic", "limit point": "accumulation point"})


@pytest.fixture(scope="module")
def profile():
    return load_profile(FIELD, ROOT)


def thm(conclusion="$u$ and $v$ are harmonic in $D$", hypotheses=None, **kw):
    return M.make(field=FIELD, type="theorem", slots=dict(
        citation_form="an analytic function has harmonic parts",
        hypotheses=hypotheses if hypotheses is not None else ["$f$ is analytic in $D$"],
        conclusion=conclusion, proofs=kw.pop("proofs", [])), **kw)


# ── canonical form (§I-4) ─────────────────────────────────────────────

def test_lexicon_substitution_then_lowercase_then_collapse():
    assert canonical_text("A  Holomorphic   function", LEX) == "a analytic function"


def test_math_is_not_lowercased_and_has_its_spaces_stripped():
    out = canonical_text("the value $ U_x = V_y $ here", LEX)
    assert "$U_x=V_y$" in out
    assert "u_x" not in out


def test_math_aliases_are_textual_only():
    assert normalise_math("a \\leq b") == "a<=b"
    assert normalise_math("dots.c") == "dots"
    # Symbolic equivalence is explicitly out of scope; these must stay different.
    assert normalise_math("z^2 - 1") != normalise_math("(z-1)(z+1)")


def test_the_hash_is_stable_under_wording_the_lexicon_governs():
    a = thm(conclusion="$u$ is harmonic and $f$ is holomorphic")
    b = thm(conclusion="$u$ is harmonic and $f$ is Analytic")
    assert canonical_hash(a, LEX) == canonical_hash(b, LEX)


def test_the_hash_separates_items_that_differ_in_one_symbol():
    assert canonical_hash(thm(conclusion="$f'(z) = 0$"), LEX) != \
        canonical_hash(thm(conclusion="$f'(z) != 0$"), LEX)


def test_normalised_statement_ignores_proofs():
    proof = dict(method="direct", conclusion="done",
                 steps=[dict(claim="$a = b$", justification=dict(kind="by-computation"))])
    assert normalised_statement(thm(), LEX) == normalised_statement(thm(proofs=[proof]), LEX)


# ── dedup outcomes (§I-4) ─────────────────────────────────────────────

TH = Thresholds()


def test_an_exact_canonical_match_auto_merges():
    existing = thm()
    d = dedup.find(thm(), [existing], LEX, TH)
    assert d.outcome is dedup.Outcome.MERGED_EXACT and d.target is existing


def test_a_merge_appends_provenance_and_keeps_the_existing_slots():
    existing = thm(conclusion="the original wording",
                   provenance=[dict(source="bc9e", kind="textbook", capture="pdf",
                                    page=3)],
                   terms_used=["harmonic"])
    incoming = thm(conclusion="a later wording",
                   provenance=[dict(source="ca-lectures", kind="board",
                                    capture="photo")],
                   terms_used=["analytic"])
    merged = dedup.merge(existing, incoming)
    assert merged.slots["conclusion"] == "the original wording"
    assert len(merged.provenance) == 2
    assert merged.terms_used == ["analytic", "harmonic"]
    assert merged.starred is True, "star inherits through provenance (A3/A6)"


def test_a_merge_does_not_duplicate_identical_provenance():
    p = dict(source="bc9e", kind="textbook", capture="pdf", page=3)
    merged = dedup.merge(thm(provenance=[p]), thm(provenance=[p]))
    assert len(merged.provenance) == 1


def test_keep_both_proofs_appends_rather_than_replaces():
    proof_a = dict(method="direct", conclusion="a",
                   steps=[dict(claim="x", justification=dict(kind="by-computation"))])
    proof_b = dict(method="contradiction", conclusion="b", contradicts="the hypothesis",
                   steps=[dict(claim="y", justification=dict(kind="by-computation"))])
    merged = dedup.merge_proof(thm(proofs=[proof_a]), thm(proofs=[proof_b]))
    assert [p["method"] for p in merged.slots["proofs"]] == ["direct", "contradiction"]


def test_a_proposal_above_auto_confirm_merges():
    existing = thm()
    incoming = thm(conclusion="$u$ and $v$ are harmonic in the domain $D$")
    d = dedup.find(incoming, [existing], LEX, TH, proposed_of=existing.id)
    assert d.outcome is dedup.Outcome.MERGED_PROPOSED and d.score >= TH.auto_confirm


def test_a_proposal_below_auto_confirm_queues_rather_than_merging():
    existing = thm()
    incoming = thm(conclusion="every bounded entire function is constant")
    d = dedup.find(incoming, [existing], LEX, TH, proposed_of=existing.id)
    assert d.outcome is dedup.Outcome.QUEUED


def test_a_proposal_naming_an_absent_item_is_queued_not_dropped():
    d = dedup.find(thm(), [], LEX, TH, proposed_of="01J9XA5T7K3M2N8P4Q6R9S0TVA")
    assert d.outcome is dedup.Outcome.QUEUED


def test_a_subset_match_merges():
    """A review board restating a fuller item's statement is the same fact."""
    full = thm(conclusion="$u$ and $v$ are harmonic in $D$ and $u$ determines $v$ "
                          "up to an additive constant")
    repeat = thm(conclusion="$u$ and $v$ are harmonic in $D$")
    d = dedup.find(repeat, [full], LEX, TH)
    assert d.outcome is dedup.Outcome.MERGED_SUBSET


def test_a_high_score_alone_never_merges():
    """Two theorems can differ in one symbol and score above auto_confirm."""
    existing = thm(conclusion="$f'(z) = 0$ for all $z in D$")
    incoming = thm(conclusion="$f'(z) != 0$ for all $z in D$")
    d = dedup.find(incoming, [existing], LEX, TH)
    assert d.outcome is dedup.Outcome.QUEUED
    assert not d.merged


def test_unrelated_items_are_distinct():
    existing = thm(conclusion="$u$ and $v$ are harmonic in $D$")
    incoming = thm(conclusion="the residue at a simple pole equals the limit "
                              "of $(z - z_0) f(z)$")
    assert dedup.find(incoming, [existing], LEX, TH).outcome is dedup.Outcome.DISTINCT


def test_items_of_different_types_never_merge():
    definition = M.make(field=FIELD, type="definition", slots=dict(
        term="harmonic", form="noun", article="a", body="$u$ and $v$ are harmonic in $D$"))
    d = dedup.find(thm(), [definition], LEX, TH)
    assert d.outcome is dedup.Outcome.DISTINCT


# ── relint (§I-5) ─────────────────────────────────────────────────────

def test_relint_rewrites_prose_across_the_whole_store(tmp_path):
    store, queues = Store(FIELD, tmp_path), Queues(tmp_path)
    old = M.make(field=FIELD, type="remark",
                 slots=dict(body="every holomorphic function is smooth"))
    store.put(old)
    report = relint(store, LEX, queues, ruling="holomorphic -> analytic")
    assert report.changed == [old.id]
    assert "analytic" in store.get(old.id).slots["body"]


def test_relint_queues_rather_than_rewriting_inside_math(tmp_path):
    store, queues = Store(FIELD, tmp_path), Queues(tmp_path)
    item = M.make(field=FIELD, type="remark",
                  slots=dict(body='the set $"holomorphic"(D)$ is closed'))
    store.put(item)
    relint(store, LEX, queues, ruling="r")
    assert queues.counts()["relint-ambiguous"] == 1
    assert '$"holomorphic"(D)$' in store.get(item.id).slots["body"]


def test_relint_dry_run_changes_nothing(tmp_path):
    store, queues = Store(FIELD, tmp_path), Queues(tmp_path)
    item = M.make(field=FIELD, type="remark", slots=dict(body="a holomorphic map"))
    store.put(item)
    report = relint(store, LEX, queues, apply=False)
    assert report.changed == [item.id]
    assert "holomorphic" in store.get(item.id).slots["body"]


# ── queues and the review loop (§I-10) ────────────────────────────────

def test_queue_entries_deduplicate_by_content(tmp_path):
    q = Queues(tmp_path)
    q.add("new-term", {"term": "quasiregular"})
    q.add("new-term", {"term": "quasiregular"})
    assert q.counts()["new-term"] == 1


def test_only_the_documented_queues_exist(tmp_path):
    with pytest.raises(KeyError):
        Queues(tmp_path).add("invented-queue", {})


def test_review_records_every_ruling_and_clears_the_entry(tmp_path):
    from knowledge_base.cli.review import read_rulings, work

    q = Queues(tmp_path)
    q.add("new-term", {"term": "quasiregular", "load_bearing": True})
    q.add("new-term", {"term": "hypoelliptic", "load_bearing": False})

    choices = iter(["canonical", "skip"])
    ruled = work(q, lambda entry, options: next(choices), only="new-term", root=tmp_path)

    assert ruled == 1
    assert q.counts()["new-term"] == 1, "a skipped entry stays in the queue"
    rulings = read_rulings(tmp_path)
    assert len(rulings) == 1 and rulings[0].choice == "canonical"
    assert rulings[0].payload["term"] == "quasiregular"


def test_the_decisions_log_is_append_only(tmp_path):
    from knowledge_base.cli.review import read_rulings, work

    q = Queues(tmp_path)
    for term in ("a", "b"):
        q.add("new-term", {"term": term})
        work(q, lambda entry, options: "canonical", only="new-term", root=tmp_path)
    assert len(read_rulings(tmp_path)) == 2


def test_a_ruling_outside_the_option_set_is_refused(tmp_path):
    q = Queues(tmp_path)
    q.add("near-duplicate", {"new_item": "x"})
    with pytest.raises(ValueError):
        work_invalid(q, tmp_path)


def work_invalid(q, root):
    from knowledge_base.cli.review import work

    return work(q, lambda entry, options: "merge-everything", only="near-duplicate",
                root=root)


def test_near_duplicate_options_are_the_four_the_plan_names():
    from knowledge_base.cli.review import OPTIONS

    assert set(OPTIONS["near-duplicate"]) == {
        "merge-keep-A", "merge-keep-B", "keep-both", "keep-both-proofs", "skip"}
