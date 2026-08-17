"""WP1.5 — the emitter, its escaping, and the store -> PDF path.

The golden test is byte-exact on purpose. The emitter's determinism is what
makes a rebuild's diff readable: if the same store can produce two different
files, nobody can tell a content change from a formatting wobble.
"""

import random
import shutil
import string
from pathlib import Path

import pytest

from knowledge_base import config
from knowledge_base.build import compile as C
from knowledge_base.build import emitter, publish
from knowledge_base.models import item as M
from knowledge_base.models.profile import load_profile
from knowledge_base.pipeline.store import Store

ROOT = Path(__file__).resolve().parents[1]
FIELD = "complex-analysis"
GOLDEN = ROOT / "tests" / "fixtures" / "golden_main.typ"
TEMPLATE = ROOT / "template" / "template-star.typ"

pytestmark_toolchain = pytest.mark.skipif(
    not C.available(ROOT), reason="typst is not installed or not on PATH")


@pytest.fixture(scope="module")
def profile():
    return load_profile(FIELD, ROOT)


@pytest.fixture(scope="module")
def settings():
    return config.load(ROOT / "config.yaml")


def step(claim="$a = b$", **just):
    just.setdefault("kind", "by-computation")
    return {"claim": claim, "justification": just}


def corpus() -> list[M.Item]:
    """A fixed store: stable ULIDs so the golden file is stable."""
    def ulid(n: int) -> str:
        # 26 Crockford characters, as ULIDs are — the ref token pattern is
        # length-exact, so a 25-character stand-in silently fails to resolve.
        return f"01J9XA5T7K3M2N8P4Q6R9S0TV{chr(ord('A') + n)}"

    return [
        M.make(id=ulid(0), field=FIELD, type="definition", topic="basics",
               created=M.datetime(2026, 1, 1, tzinfo=M.timezone.utc),
               updated=M.datetime(2026, 1, 1, tzinfo=M.timezone.utc),
               provenance=[dict(source="bc9e", kind="textbook", capture="pdf", page=1)],
               slots=dict(term="domain", form="noun", article="a",
                          body="a non-empty open connected set")),
        M.make(id=ulid(1), field=FIELD, type="definition", topic="basics",
               created=M.datetime(2026, 1, 1, tzinfo=M.timezone.utc),
               updated=M.datetime(2026, 1, 1, tzinfo=M.timezone.utc),
               provenance=[dict(source="bc9e", kind="textbook", capture="pdf", page=2)],
               slots=dict(term="harmonic", form="predicate",
                          subject="A function $u(x, y)$", scope="in $D$",
                          context="$D$ be a domain",
                          body="it has continuous second partials and "
                               "$nabla^2 u = 0$ in $D$")),
        M.make(id=ulid(2), field=FIELD, type="theorem", topic="harmonic",
               title="Harmonic Parts Theorem",
               created=M.datetime(2026, 1, 1, tzinfo=M.timezone.utc),
               updated=M.datetime(2026, 1, 1, tzinfo=M.timezone.utc),
               provenance=[dict(source="ca-lectures", kind="board", capture="photo")],
               slots=dict(
                   citation_form="the real and imaginary parts of an analytic "
                                 "function are harmonic in its domain",
                   hypotheses=["$f = u + i v$ is analytic in $D$"],
                   conclusion="$u$ and $v$ are harmonic in $D$",
                   proofs=[dict(method="direct", conclusion="$u$ and $v$ are harmonic",
                                steps=[step("$u_x = v_y$", kind="by-ref", ref=ulid(3)),
                                       step("$u_(x x) + u_(y y) = 0$")])])),
        M.make(id=ulid(3), field=FIELD, type="proposition", topic="harmonic",
               created=M.datetime(2026, 1, 1, tzinfo=M.timezone.utc),
               updated=M.datetime(2026, 1, 1, tzinfo=M.timezone.utc),
               provenance=[dict(source="bc9e", kind="textbook", capture="pdf", page=3)],
               slots=dict(citation_form="the Cauchy–Riemann equations hold for an "
                                        "analytic function",
                          hypotheses=[], conclusion="$u_x = v_y$ and $u_y = -v_x$",
                          proofs=[])),
        M.make(id=ulid(4), field=FIELD, type="remark", topic="harmonic",
               created=M.datetime(2026, 1, 1, tzinfo=M.timezone.utc),
               updated=M.datetime(2026, 1, 1, tzinfo=M.timezone.utc),
               provenance=[dict(source="bc9e", kind="textbook", capture="raster")],
               slots=dict(body="the converse holds on a simply connected domain, "
                               "as in {ref:%s}" % ulid(3))),
    ]


# ── escaping ──────────────────────────────────────────────────────────

def test_math_runs_pass_through_untouched():
    text = "the value $f'(z_0) = u_x + i v_x$ is finite"
    assert "$f'(z_0) = u_x + i v_x$" in emitter.escape_prose(text)


def test_typst_markup_in_prose_is_escaped():
    out = emitter.escape_prose("a #let x = 1 and [brackets] and *stars*")
    for ch in ("#", "[", "]", "*"):
        assert f"\\{ch}" in out


def test_line_comments_cannot_survive():
    """A stray `//` deletes the rest of the line, silently."""
    assert "\\/\\/" in emitter.escape_prose("the quotient a//b")


def test_frame_markup_is_not_escaped(profile):
    """The bold of a defined term is markup frames emits, not slot content."""
    plan = emitter.plan([], profile)
    item = corpus()[0]
    out = emitter.render_item(item, plan, emitter.frames.Doc({}, set()), profile)
    assert "*domain*" in out and "\\*domain\\*" not in out


def test_markup_inside_slot_text_is_escaped(profile):
    plan = emitter.plan([], profile)
    item = M.make(field=FIELD, type="remark",
                  slots=dict(body="a #box[injected] *bold* attempt"))
    out = emitter.render_item(item, plan, emitter.frames.Doc({}, set()), profile)
    assert "\\#box" in out and "\\*bold\\*" in out


@pytestmark_toolchain
def test_adversarial_strings_compile(tmp_path, profile):
    """§I-11 property test: a remark body of random adversarial text must
    compile. Escaping that is nearly right is escaping that fails on one item in
    a thousand, years from now, in a nightly run nobody is watching."""
    alphabet = string.ascii_letters + string.digits + " " + "\\#$[]{}@*_<>~`/^\"'%&|+-=.,:;()"
    rng = random.Random(20260804)
    for i in range(12):
        body = "".join(rng.choice(alphabet) for _ in range(120)).replace("$", "")
        item = M.make(field=FIELD, type="remark", slots=dict(body=body))
        plan = emitter.plan([], profile)
        rendered = emitter.render_item(item, plan, emitter.frames.Doc({}, set()), profile)
        result = C.smoke(rendered, tmp_path / f"case{i}", TEMPLATE, root=ROOT)
        assert result.ok, f"case {i} failed to compile:\n{body!r}\n{result.stderr[:800]}"


# ── ordering and labels ───────────────────────────────────────────────

def test_ordering_follows_the_outline_then_the_page(profile):
    outlined = profile.model_copy(update={
        "outline": profile.outline.model_validate({"chapters": [
            {"key": "c1", "title": "Foundations", "topics": ["basics"]},
            {"key": "c2", "title": "Harmonic functions", "topics": ["harmonic"]}]})})
    plan = emitter.plan(corpus(), outlined)
    ids = [e["id"] for e in plan.events if e["kind"] == "item"]
    labels = [plan.label(i) for i in ids]
    assert labels[:2] == ["def-1.1", "def-1.2"]
    by_id = {i.id: i for i in corpus()}
    theorem = next(i for i in by_id.values() if i.type.value == "theorem")
    assert plan.label(theorem.id).startswith("thm-2."), "chapter 2 restarts numbering"


def test_unnumbered_items_carry_no_label(profile):
    plan = emitter.plan(corpus(), profile)
    remark = corpus()[4]
    assert plan.label(remark.id) is None


def test_refs_resolve_to_labels_never_to_numbers(profile):
    out = emitter.emit(corpus(), profile, "Complex Analysis")
    assert "{ref:" not in out
    assert "@prop-" in out


def test_a_ref_to_an_absent_item_is_dropped_not_rendered(profile):
    """§I-8.8 + A20: an unresolved ref must never reach the page as vague prose."""
    item = M.make(field=FIELD, type="remark",
                  slots=dict(body="as in {ref:01J9XA5T7K3M2N8P4Q6R9S0TVZ}"))
    out = emitter.emit([item], profile, "t")
    assert "{ref:" not in out and "@" not in out


def test_the_star_is_derived_from_board_provenance(profile):
    out = emitter.emit(corpus(), profile, "Complex Analysis")
    assert "star: true" in out
    assert out.count("star: true") == 1, "only the board-sourced item is starred"


def test_open_and_flagged_items_are_not_rendered(profile):
    items = corpus()
    items[0] = items[0].model_copy(update={"status": M.Status.FLAGGED})
    items[1] = items[1].model_copy(update={"status": M.Status.OPEN})
    out = emitter.emit(items, profile, "t")
    assert "*domain*" not in out and "*harmonic*" not in out


# ── determinism ───────────────────────────────────────────────────────

def test_emission_is_byte_identical_across_runs(profile):
    a = emitter.emit(corpus(), profile, "Complex Analysis")
    b = emitter.emit(list(reversed(corpus())), profile, "Complex Analysis")
    assert a == b, "emission must not depend on the order items were loaded"


def test_golden_file(profile):
    out = emitter.emit(corpus(), profile, "Complex Analysis")
    if not GOLDEN.exists():                       # first run records the golden
        GOLDEN.write_text(out, encoding="utf-8", newline="")
    assert out == GOLDEN.read_text(encoding="utf-8"), (
        "emitter output changed. If the change is intended, delete "
        "tests/fixtures/golden_main.typ and re-run to re-record it.")


# ── the whole path ────────────────────────────────────────────────────

@pytestmark_toolchain
def test_store_to_pdf(tmp_path, settings):
    for name in ("fields", "template", "generated"):
        shutil.copytree(ROOT / name, tmp_path / name)
    (tmp_path / "fonts").symlink_to((ROOT / "fonts").resolve())

    store = Store(FIELD, tmp_path)
    for item in corpus():
        store.put(item)

    result = publish.build_field(FIELD, settings, tmp_path)
    assert result.ok, result.stderr[:2000]
    assert result.pdf.exists() and result.pdf.stat().st_size > 1000
    assert result.item_count == 5


@pytestmark_toolchain
def test_numbering_matches_the_compiler(tmp_path, profile):
    """The simulation's labels must equal the ones typst assigns — the same
    parity guarantee WP0.2 established, now on emitter output."""
    for name in ("template",):
        shutil.copytree(ROOT / name, tmp_path / name)
    work = tmp_path / "doc"
    work.mkdir()
    shutil.copy(TEMPLATE, work)
    (work / "symbols-gen.typ").write_text("", encoding="utf-8", newline="")
    plan = emitter.plan(corpus(), profile)
    (work / "main.typ").write_text(emitter.emit(corpus(), profile, "t"), encoding="utf-8",
                                   newline="")

    assert C.compile_doc(work / "main.typ", root=ROOT).ok
    queried = C.query(work / "main.typ", 'figure.where(kind: "math-env")', root=ROOT)
    actual = [e["label"].strip("<>") for e in queried if e.get("label")]
    expected = [plan.label(e["id"]) for e in plan.events
                if e["kind"] == "item" and plan.label(e["id"])]
    assert actual == expected
