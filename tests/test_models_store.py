"""WP1.1 — the data model and the store.

The store holds work derived from originals that cannot be recaptured, so the
write path is tested for atomicity, not just for correctness.
"""

import json
import os
import subprocess
from pathlib import Path

import pytest
from pydantic import ValidationError

from knowledge_base.models import item as M
from knowledge_base.models import schemas
from knowledge_base.models.profile import load_profile
from knowledge_base.models.slots import Justification, Proof, Step
from knowledge_base.pipeline.store import Store, commit

ROOT = Path(__file__).resolve().parents[1]

DEF = dict(term="domain", form="noun", article="a",
           body="a non-empty open connected set")
THM = dict(citation_form="the real and imaginary parts of an analytic function are harmonic",
           hypotheses=["$f = u + i v$ is analytic in $D$"],
           conclusion="$u$ and $v$ are harmonic in $D$")


def mk(field="complex-analysis", type="definition", slots=None, **kw):
    return M.make(field=field, type=type, slots=slots if slots is not None else dict(DEF), **kw)


# ── model ─────────────────────────────────────────────────────────────

def test_slots_are_validated_against_the_item_type():
    with pytest.raises(ValidationError):
        mk(type="theorem", slots=dict(DEF))


def test_definition_predicate_form_requires_a_subject():
    with pytest.raises(ValidationError):
        mk(slots=dict(term="harmonic", form="predicate", body="$nabla^2 u = 0$"))
    ok = mk(slots=dict(term="harmonic", form="predicate", subject="A function $u(x, y)$",
                       scope="in $D$", body="$nabla^2 u = 0$"))
    assert ok.slots["subject"] == "A function $u(x, y)$"


def test_citation_form_is_required_on_every_result(capfd):
    """A21: without it a citation has to be composed, which §2.1 forbids."""
    with pytest.raises(ValidationError):
        mk(type="theorem", slots={k: v for k, v in THM.items() if k != "citation_form"})


def test_justification_fields_must_match_their_kind():
    Justification(kind="by-definition", term="analytic")
    Justification(kind="by-fact", fact="a limit is unique", ref="01J9X")  # A20 pairing
    with pytest.raises(ValidationError):
        Justification(kind="by-definition")                    # missing term
    with pytest.raises(ValidationError):
        Justification(kind="by-hypothesis", ref="01J9X")       # ref not permitted
    with pytest.raises(ValidationError):
        Justification(kind="by-computation", fact="x")         # fact not permitted


def test_transition_slot_only_carries_the_three_authored_words():
    """The other transitions are derived from the justification kind by frames."""
    Justification(kind="by-computation", transition="Note that")
    with pytest.raises(ValidationError):
        Justification(kind="by-computation", transition="Therefore")


def test_proof_substructure_is_required_by_method():
    step = Step(claim="$a = b$", justification=Justification(kind="by-computation"))
    with pytest.raises(ValidationError):
        Proof(method="induction", conclusion="$P(n)$")
    with pytest.raises(ValidationError):
        Proof(method="cases", cases=[dict(condition="$x > 0$", steps=[step])])
    Proof(method="double-inclusion",
          subset=dict(steps=[step], conclusion="$I J subset.eq I sect J$"),
          superset=dict(steps=[], conclusion="always true"),
          conclusion="$I J = I sect J$")
    Proof(method="verify-criteria", definition="the definition of an ideal",
          criteria=[dict(name="closed under addition", steps=[step])],
          conclusion="the intersection is an ideal")


def test_counterexample_must_establish_one_of_the_two_admitted_things():
    with pytest.raises(ValidationError):
        mk(type="counterexample", slots=dict(target="01J9X", establishes="hypothesis-necessary",
                                             witness="$f(z) = |z|^2$", witness_properties="x"))
    mk(type="counterexample", slots=dict(target="01J9X", establishes="hypothesis-necessary",
                                         hypothesis="continuity of the partials",
                                         witness="$f(z) = |z|^2$", witness_properties="x"))


def test_star_is_derived_from_board_provenance_and_overridable():
    board = dict(kind="board", capture="photo")
    text = dict(kind="textbook", capture="pdf", page=12)
    assert mk(provenance=[text]).starred is False
    assert mk(provenance=[text, board]).starred is True
    assert mk(provenance=[text, board], exam_star=False).starred is False
    assert mk(provenance=[text], exam_star=True).starred is True


def test_schema_generation_covers_every_taxonomy_type():
    tax = load_profile("complex-analysis", ROOT).taxonomy
    s = schemas.for_types(tax.keys())
    for key in tax.keys():
        assert key in s
    assert json.loads(schemas.canonical_json(s)) == s


def test_taxonomy_is_the_emitter_allowlist():
    tax = load_profile("complex-analysis", ROOT).taxonomy
    assert tax.allows("theorem") and not tax.allows("exercise")
    assert tax.entry("remark").numbered is False
    assert tax.entry("theorem").numbered is True
    # A9: the excluded classes are policy, and both prompts render from them.
    assert {e.key for e in tax.excluded} >= {
        "question", "problem", "solution", "worked-demonstration", "recall-repeat",
        "narrative", "non-content", "foreign-subject", "source-correction"}


# ── store ─────────────────────────────────────────────────────────────

def test_round_trip(tmp_path):
    st = Store("complex-analysis", tmp_path)
    it = mk(type="theorem", slots=dict(THM), title="Harmonic parts",
            provenance=[dict(source="bc9e", kind="textbook", capture="pdf", page=153)])
    st.put(it)
    back = st.get(it.id)
    assert back == it
    assert back.provenance[0].page == 153


def test_put_is_atomic(tmp_path, monkeypatch):
    """A crash mid-write must leave the previous version intact, not a fragment."""
    st = Store("complex-analysis", tmp_path)
    it = mk()
    st.put(it)
    good = st.path(it.id).read_text(encoding="utf-8")

    real_replace = os.replace

    def boom(src, dst):
        raise OSError("simulated crash between write and rename")

    monkeypatch.setattr(os, "replace", boom)
    with pytest.raises(OSError):
        st.put(it.model_copy(update={"title": "half-written"}))
    monkeypatch.setattr(os, "replace", real_replace)

    assert st.path(it.id).read_text(encoding="utf-8") == good
    assert st.get(it.id).title is None


def test_ids_are_creation_sortable():
    ids = [M.new_id() for _ in range(50)]
    assert ids == sorted(ids)


def test_buildable_excludes_flagged_and_open(tmp_path):
    st = Store("complex-analysis", tmp_path)
    for status in ("active", "open", "flagged", "superseded"):
        st.put(mk(status=status))
    assert [i.status.value for i in st.buildable()] == ["active"]


def test_supersede_keeps_the_item(tmp_path):
    st = Store("complex-analysis", tmp_path)
    old, new = mk(), mk()
    st.put(old)
    st.supersede(old.id, new.id)
    assert st.exists(old.id)
    assert st.get(old.id).superseded_by == new.id


def test_wrong_field_is_refused(tmp_path):
    st = Store("complex-analysis", tmp_path)
    with pytest.raises(ValueError):
        st.put(mk(field="ordinary-differential-equations"))


def test_commit_helper(tmp_path):
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.email", "t@example.com"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.name", "t"], cwd=tmp_path, check=True)
    st = Store("complex-analysis", tmp_path)
    p = st.put(mk())
    assert commit([p], "add item", root=tmp_path) is True
    assert commit([p], "no change", root=tmp_path) is False
