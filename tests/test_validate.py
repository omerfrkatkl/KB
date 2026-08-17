"""WP1.4 — validation. Each check must route its failure, not merely reject."""

from pathlib import Path

import pytest

from knowledge_base.models import item as M
from knowledge_base.models.profile import load_profile
from knowledge_base.pipeline.validate import (
    Route,
    apply_lexicon,
    check_completeness,
    check_refs,
    check_stg,
    prose_runs,
    run_rules,
    slot_texts,
    validate,
)

ROOT = Path(__file__).resolve().parents[1]
FIELD = "complex-analysis"


@pytest.fixture(scope="module")
def profile():
    return load_profile(FIELD, ROOT)


def mk(type="definition", slots=None, **kw):
    slots = slots or dict(term="domain", form="noun", article="a",
                          body="a non-empty open connected set")
    return M.make(field=FIELD, type=type, slots=slots, **kw)


def thm(**over):
    base = dict(citation_form="an analytic function has harmonic parts",
                hypotheses=["$f$ is analytic in $D$"],
                conclusion="$u$ and $v$ are harmonic in $D$", proofs=[])
    base.update(over)
    return base


# ── 2. slot text grammar ──────────────────────────────────────────────

def test_unbalanced_math_routes_to_retry():
    f = check_stg("the value $f(z)", "body")
    assert f and f[0].route is Route.RETRY


def test_ref_token_must_be_a_ulid():
    assert not check_stg("see {ref:01J9XA5T7K3M2N8P4Q6R9S0TVW}", "body")
    bad = check_stg("see {ref:theorem 2.4}", "body")
    assert bad and bad[0].route is Route.RETRY


def test_line_breaks_and_markup_are_not_slot_text():
    assert check_stg("one\ntwo", "body")[0].route is Route.RETRY
    assert check_stg("- a list item", "body")[0].route is Route.RETRY


def test_prose_runs_exclude_math():
    assert prose_runs("let $x = 1$ be so") == ["let ", " be so"]


def test_slot_texts_reach_into_proofs():
    item = mk(type="theorem", slots=thm(proofs=[dict(
        method="direct", conclusion="done",
        steps=[dict(claim="$a = b$", justification=dict(kind="by-computation"))])]))
    paths = dict(slot_texts(item))
    assert any(p.endswith("claim") for p in paths)
    assert "citation_form" in paths


# ── 4. lexicon ────────────────────────────────────────────────────────

def test_substitution_is_word_bounded_and_case_preserving():
    banned = {"holomorphic": "analytic"}
    out, applied = apply_lexicon("Holomorphic on $D$", banned)
    assert out == "Analytic on $D$" and applied == [("holomorphic", "analytic")]
    assert apply_lexicon("holomorphically", banned)[0] == "holomorphically"


def test_substitution_never_touches_math():
    out, _ = apply_lexicon("the set $limit point$ is a limit point",
                           {"limit point": "accumulation point"})
    assert "$limit point$" in out
    assert out.endswith("is a accumulation point")


def test_longest_match_wins():
    banned = {"singularity": "singular point",
              "isolated singularity": "isolated singular point"}
    out, _ = apply_lexicon("an isolated singularity", banned)
    assert out == "an isolated singular point"


# ── 4A. the rule engine ───────────────────────────────────────────────

def test_forbidden_word_flags_and_is_not_rewritten(profile):
    rules = [r for r in profile.validators.rules if r.id == "forbid-clearly"]
    text, findings, applied = run_rules("Clearly the map is analytic", rules)
    assert text == "Clearly the map is analytic", "a ban is not a substitution"
    assert findings[0].route is Route.FLAG and not applied


def test_fixed_phrases_are_not_violations(profile):
    rules = [r for r in profile.validators.rules if r.id == "forbid-so"]
    assert not run_rules("the terms $a_1$, $a_2$, and so on", rules)[1]
    assert run_rules("the map is continuous, so it is bounded", rules)[1]


def test_hyphenation_is_fixed_deterministically(profile):
    rules = [r for r in profile.validators.rules if r.id == "hyph-non-empty"]
    text, findings, applied = run_rules("a nonempty open set", rules)
    assert text == "a non-empty open set"
    assert findings[0].route is Route.FIXED and applied


def test_abbreviations_expand(profile):
    rules = [r for r in profile.validators.rules if r.id == "abbr-mvt"]
    assert run_rules("by the MVT", rules)[0] == "by the Mean Value Theorem"


def test_notation_rules_flag_rather_than_rewrite(profile):
    rules = [r for r in profile.validators.rules if r.kind == "notation"][:1]
    if rules:
        _, findings, applied = run_rules(rules[0].pattern.replace("\\", ""), rules)
        assert not applied


# ── 6. completeness ───────────────────────────────────────────────────

def test_an_empty_proofs_list_is_not_incompleteness():
    """Sources legitimately state results without argument (§I-3)."""
    assert not check_completeness(mk(type="theorem", slots=thm(proofs=[])))


def test_a_proof_without_a_conclusion_is_open():
    item = mk(type="theorem", slots=thm(proofs=[dict(
        method="direct",
        steps=[dict(claim="$a = b$", justification=dict(kind="by-computation"))])]))
    f = check_completeness(item)
    assert f and f[0].route is Route.OPEN


def test_a_declared_but_empty_case_is_open():
    item = mk(type="theorem", slots=thm(proofs=[dict(
        method="cases", conclusion="done",
        cases=[dict(condition="$x > 0$", steps=[dict(
            claim="a", justification=dict(kind="by-computation"))]),
               dict(condition="$x <= 0$", steps=[])])]))
    assert any(f.route is Route.OPEN for f in check_completeness(item))


# ── 8. reference integrity ────────────────────────────────────────────

def test_unresolved_refs_route_to_the_pending_ref_queue():
    ulid = "01J9XA5T7K3M2N8P4Q6R9S0TVW"
    item = mk(slots=dict(term="t", form="noun", article="a",
                         body="as in {ref:%s}" % ulid))
    assert check_refs(item, set())[0].route is Route.PENDING_REF
    assert not check_refs(item, {ulid})


def test_a_ref_inside_a_proof_flags_the_item_too():
    ulid = "01J9XA5T7K3M2N8P4Q6R9S0TVW"
    item = mk(type="theorem", slots=thm(proofs=[dict(
        method="direct", conclusion="done",
        steps=[dict(claim="$a = b$",
                    justification=dict(kind="by-ref", ref=ulid))])]))
    assert check_refs(item, set())[0].route is Route.PENDING_REF


# ── the ordered pass ──────────────────────────────────────────────────

def test_a_clean_item_validates_active(profile):
    r = validate(mk(), profile)
    assert r.ok and r.status().value == "active"


def test_substitutions_are_written_back_into_the_item(profile):
    item = mk(slots=dict(term="analytic function", form="noun", article="an",
                         body="a holomorphic function on a nonempty open set"))
    r = validate(item, profile)
    assert "analytic" in r.item.slots["body"]
    assert "non-empty" in r.item.slots["body"]
    assert r.substitutions


def test_a_load_bearing_unknown_term_flags_the_item(profile):
    item = mk(slots=dict(term="quasiregular map", form="noun", article="a",
                         body="a map of bounded distortion"),
              terms_used=["quasiregular map"])
    r = validate(item, profile)
    flagged = [f for f in r.findings if f.check == "lexicon.unknown-term"]
    assert flagged and flagged[0].route is Route.FLAG
    assert r.status().value == "flagged"


def test_an_incidental_unknown_term_queues_but_does_not_flag(profile):
    item = mk(type="theorem",
              slots=thm(proofs=[dict(method="direct", conclusion="done", steps=[
                  dict(claim="the quasiregular case is different",
                       justification=dict(kind="by-computation"))])]),
              terms_used=["quasiregular"])
    r = validate(item, profile)
    unknown = [f for f in r.findings if f.check == "lexicon.unknown-term"]
    assert unknown and unknown[0].route is Route.NEW_TERM
    assert r.status().value == "active"


def test_a_type_outside_the_taxonomy_is_never_force_fitted(profile):
    item = mk()
    narrowed = profile.model_copy(update={
        "taxonomy": profile.taxonomy.model_copy(update={
            "types": [t for t in profile.taxonomy.types if t.key != "definition"]})})
    r = validate(item, narrowed)
    assert not r.ok
    assert r.findings[0].route is Route.UNCLASSIFIED
