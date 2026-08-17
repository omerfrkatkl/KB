"""WP1.4A — the rule compiler.

The golden case is `tests/fixtures/rules_mini/`, a miniature rule set that
exercises every shape the compiler recognises and, more importantly, the shapes
it must refuse. The refusals matter more than the acceptances: a wrong entry in
`banned:` is a silent, automatic, corpus-wide rewrite.
"""

from pathlib import Path

import pytest

from knowledge_base.rules import parse
from knowledge_base.rules.compile_rules import compile_field, outputs, run

ROOT = Path(__file__).resolve().parents[1]
MINI = ROOT / "tests" / "fixtures" / "rules_mini"


@pytest.fixture(scope="module")
def mini(monkeypatch_module=None):
    import knowledge_base.rules.compile_rules as cr

    saved = dict(cr.FIELD_DOCS)
    cr.FIELD_DOCS["mini"] = "fields/mini.txt"
    try:
        yield compile_field("mini", MINI)
    finally:
        cr.FIELD_DOCS.clear()
        cr.FIELD_DOCS.update(saved)


# ── what must compile ─────────────────────────────────────────────────

def test_single_sentence_pairs_become_substitutions(mini):
    assert mini.lexicon["banned"]["holomorphic"] == "analytic"
    assert mini.lexicon["banned"]["regular"] == "analytic", "the `or` continuation"


def test_hyphenation_rules_are_compiled(mini):
    ids = {r["id"] for r in mini.validators["rules"]}
    assert {"hyph-non-zero", "hyph-non-empty", "hyph-well-defined"} <= ids
    rule = next(r for r in mini.validators["rules"] if r["id"] == "hyph-non-zero")
    assert rule["fix"] == "non-zero" and rule["pattern"] == r"\bnonzero\b"


def test_forbidden_words_carry_their_fixed_phrase_exceptions(mini):
    rule = next(r for r in mini.validators["rules"] if r["id"] == "forbid-so")
    assert rule["fix"] is None, "a ban is not a substitution"
    assert rule["except_phrases"] == ["and so on", "do so"]


def test_abbreviations_expand(mini):
    rule = next(r for r in mini.validators["rules"] if r["id"] == "abbr-mvt")
    assert rule["fix"] == "Mean Value Theorem"


def test_term_first_shape_is_read(mini):
    ids = {r["id"] for r in mini.validators["rules"]}
    assert any(i.startswith("sub-i-e") for i in ids), '"that is" — ALWAYS in full'


def test_notation_pairs_go_to_symbols_and_are_flag_only(mini):
    forms = {f["always"]: f for f in mini.symbols["forms"]}
    assert "$overline(z)$" in forms
    assert forms["$overline(z)$"]["never"] == ["$z^*$"]
    nota = [r for r in mini.validators["rules"] if r["kind"] == "notation"]
    assert nota and all(r["fix"] is None for r in nota), \
        "a notation rule may straddle the math boundary; substituting could corrupt it"


# ── what must NOT compile ─────────────────────────────────────────────

def test_proof_style_reaches_none_of_the_three_targets(mini):
    """§I-5A: Proof Style's destination is frames. Its rulings are frame
    templates written in the same ALWAYS/NEVER shape as terminology, and
    compiling them would install `Therefore -> Hence` store-wide."""
    banned = mini.lexicon["banned"]
    assert "Therefore" not in banned and "Then" not in banned
    assert not any("Proof Style" in r["section"] for r in mini.validators["rules"])
    assert not any("Proof Style" in f["section"] for f in mini.symbols["forms"])


def test_a_moved_stub_is_never_parsed(mini):
    """The stub preserves section numbering; its text describes a withdrawn rule."""
    assert not any("§15.2" in r["section"] for r in mini.validators["rules"])
    assert "Then" not in mini.lexicon["banned"]


def test_a_semantic_never_is_not_a_terminology_pair(mini):
    """Common §16 bans a *meaning*, not a word: "positive" stays legal."""
    assert "positive" not in mini.lexicon["banned"]


def test_a_ruling_spread_over_two_sentences_is_a_proposal_not_a_rule(mini):
    """§2 of the fixture states branch cut / branch point / NEVER branchcut in
    three sentences. Associating the NEVER with the nearest ALWAYS gives
    `branchcut -> branch point`, which is wrong."""
    assert "branchcut" not in mini.lexicon["banned"]
    proposals = {(c["proposed_banned"], c["proposed_canonical"])
                 for c in mini.candidates["candidates"]}
    assert ("branchcut", "branch point") in proposals
    assert all(c["evidence"] for c in mini.candidates["candidates"])


def test_a_substitution_that_would_rewrite_its_own_replacement_is_refused(mini):
    """`entire -> an entire function` would produce "an an entire function
    function". It is a real rule about bare usage that a word-boundary rewrite
    cannot express, so it becomes a proposal."""
    assert "entire" not in mini.lexicon["banned"]


def test_a_substitution_that_would_corrupt_a_proper_name_is_refused(mini):
    """`transformation -> mapping` (real, §5.5 of the CA document) would turn
    "linear fractional transformation" into "linear fractional mapping"."""
    assert "transformation" not in mini.lexicon["banned"]
    assert any(c["proposed_banned"] == "transformation"
               for c in mini.candidates["candidates"])


# ── the real documents ────────────────────────────────────────────────

def test_real_documents_compile(tmp_path):
    compiled = compile_field("complex-analysis", ROOT / "rules")
    assert len(compiled.lexicon["banned"]) >= 15
    assert len(compiled.validators["rules"]) >= 40
    # Every §14 forbidden word and every §13 compound must be present: those two
    # sections are the ones the validator leans on hardest.
    ids = {r["id"] for r in compiled.validators["rules"]}
    assert {"forbid-we", "forbid-clearly", "forbid-thus", "forbid-so",
            "forbid-obviously", "forbid-trivially", "forbid-it-follows-that",
            "forbid-one-can-show", "forbid-it-is-easy-to-see"} <= ids
    assert len([i for i in ids if i.startswith("hyph-")]) == 12


def test_known_correct_pairs_are_present_and_known_wrong_ones_absent():
    """Spot-check of 20 entries against the documents, as WP1.4A's DoD asks."""
    banned = compile_field("complex-analysis", ROOT / "rules").lexicon["banned"]
    for variant, canonical in {
        "holomorphic": "analytic",
        "limit point": "accumulation point",
        "isolated singularity": "isolated singular point",
        "essential singularity": "essential singular point",
        "removable singularity": "removable singular point",
        "pole of order 1": "simple pole",
        "simply connected region": "simply connected domain",
        "multiply connected region": "multiply connected domain",
        "path-independent": "independent of path",
        "conformal map": "conformal mapping",
        "Jordan arc": "simple arc",
        "Jordan curve": "simple closed curve",
        "Schwarz Reflection Principle": "Reflection Principle",
        "Poisson integral kernel": "Poisson kernel",
        "outward normal derivative": "normal derivative",
        "Dirichlet boundary value problem": "Dirichlet problem",
        "Neumann boundary value problem": "Neumann problem",
    }.items():
        assert banned.get(variant) == canonical, f"{variant} -> {banned.get(variant)}"

    # Wrong pairs an earlier paragraph-level parser produced. Each would have
    # been an automatic, corpus-wide rewrite in the wrong direction.
    # `line integral` was enforced until 2026-08-11 and is now demoted: real
    # line integrals appear in the Green's theorem step of Cauchy–Goursat.
    for wrong in ("domain", "function", "infinity", "counterclockwise direction",
                  "Schwarz–Christoffel Transformation", "line integral"):
        assert wrong not in banned, f"{wrong!r} must never be an automatic substitution"


def test_ode_document_compiles_too():
    banned = compile_field("ordinary-differential-equations", ROOT / "rules").lexicon["banned"]
    assert banned.get("auxiliary equation") == "characteristic equation"
    assert banned.get("Heaviside function") == "unit step function"


# ── scoped bans (§7.4) ────────────────────────────────────────────────

def test_a_scoped_ban_is_a_proposal_not_an_enforced_pair():
    """§7.4 scopes `deleted neighborhood -> punctured disk` to
    $0 < |z - z_0| < R$. The compiler represents unconditional pairs only, so
    enforcing it would fire on a neighborhood of infinity — $|z| > 1/epsilon$
    per §17.1, which is not a disk — and produce a false statement."""
    compiled = compile_field("complex-analysis", ROOT / "rules")
    assert "deleted neighborhood" not in compiled.lexicon["banned"]
    assert not [r for r in compiled.validators["rules"]
                if r["id"] == "sub-deleted-neighborhood"]

    proposal = next(c for c in compiled.candidates["candidates"]
                    if c["proposed_banned"] == "deleted neighborhood")
    assert proposal["proposed_canonical"] == "punctured disk"
    assert proposal["demoted"] is True
    assert proposal["section"] == "complex-analysis §7.4"
    assert "$0 < |z - z_0| < R$" in proposal["evidence"], "source sentence attached"


def test_the_scoped_ban_reaches_the_new_term_queue(tmp_path):
    """A demotion that only lands in a generated file is a demotion nobody
    rules on. Write mode raises it; --check stays side-effect free, because the
    pre-commit hook runs it."""
    import shutil

    from knowledge_base.pipeline.queues import Queues

    shutil.copy(ROOT / "config.yaml", tmp_path / "config.yaml")
    shutil.copytree(ROOT / "rules", tmp_path / "rules")

    assert run(root=tmp_path, check=True) == 1
    assert Queues(tmp_path).counts()["new-term"] == 0, "--check must not write"

    assert run(root=tmp_path) == 0
    entries = Queues(tmp_path).list("new-term")
    payload = next(e.payload for e in entries
                   if e.payload["term"] == "deleted neighborhood")
    assert payload["proposed_canonical"] == "punctured disk"
    assert "1/epsilon" in payload["why"], "the bespoke reason, not the generic one"

    before = Queues(tmp_path).counts()["new-term"]
    run(root=tmp_path)
    assert Queues(tmp_path).counts()["new-term"] == before, \
        "re-running must not multiply entries"


def test_a_neighborhood_of_infinity_survives_validation():
    """The regression this whole change exists for. §17.1's neighborhood of
    infinity is $|z| > 1/epsilon$; rewriting it to "punctured disk" states
    something false, and nothing downstream could detect it."""
    from knowledge_base.models.profile import load_profile
    from knowledge_base.pipeline.validate import apply_lexicon, run_rules

    profile = load_profile("complex-analysis", ROOT)
    for text in ("a deleted neighborhood of infinity, where |z| > 1/epsilon",
                 "a deleted neighborhood of infinity, where $|z| > 1/epsilon$"):
        assert apply_lexicon(text, profile.lexicon.banned)[0] == text
        assert run_rules(text, profile.validators.rules)[0] == text

    # The scoped sense is not silently rewritten either — it is now a ruling
    # the owner makes, not one the compiler makes for them.
    scoped = "$f$ is analytic in a deleted neighborhood of $z_0$"
    assert apply_lexicon(scoped, profile.lexicon.banned)[0] == scoped


def test_the_three_surveyed_scoped_pairs_got_three_different_treatments():
    """The survey found three flattened pairs; each needed a different answer,
    and lumping them together would have been wrong three ways.

    `line integral` was judged safe to enforce and then judged wrong on
    2026-08-11: real line integrals appear in this subject, in the Green's
    theorem step of the Cauchy–Goursat proof. It is demoted. `degree` was a
    rule-document defect: the bare word is correct in its own sense, so the
    document now bans the two wrong phrases instead. `phase space` is scoped by
    a dimension nothing can inspect, so it is a proposal."""
    ca = compile_field("complex-analysis", ROOT / "rules").lexicon["banned"]
    ode = compile_field("ordinary-differential-equations",
                        ROOT / "rules").lexicon["banned"]
    assert "line integral" not in ca
    assert "degree" not in ode
    assert not [b for b in ode if b.startswith("degree")]
    assert "phase space" not in ode


# ── failing closed on scoped bans ─────────────────────────────────────

def test_the_bare_word_degree_is_never_rewritten():
    """A polynomial has a degree; a differential equation has an order. The
    bare ban turned "the degree of a polynomial" into "the order of the
    equation of a polynomial"."""
    from knowledge_base.models.profile import load_profile
    from knowledge_base.pipeline.validate import apply_lexicon, run_rules

    profile = load_profile("ordinary-differential-equations", ROOT)
    assert "degree" not in profile.lexicon.banned, "the bare pair is gone"
    for text in ("the degree of a polynomial",
                 "a second degree term in the expansion",
                 "the degree of a polynomial and the order of the equation"):
        assert apply_lexicon(text, profile.lexicon.banned)[0] == text
        assert run_rules(text, profile.validators.rules)[0] == text


def test_phase_space_survives_validation():
    """§14.1 is scoped by dimension. A three-dimensional system has a phase
    space, and no substitution can inspect the dimension."""
    from knowledge_base.models.profile import load_profile
    from knowledge_base.pipeline.validate import apply_lexicon, run_rules

    profile = load_profile("ordinary-differential-equations", ROOT)
    text = "the phase space of a three-dimensional autonomous system"
    assert apply_lexicon(text, profile.lexicon.banned)[0] == text
    assert run_rules(text, profile.validators.rules)[0] == text


def test_a_qualifier_demotes_unless_the_pair_is_allowlisted(tmp_path):
    """The fail-closed default, and the authored override of it."""
    rules_dir = tmp_path / "rules"
    (rules_dir / "fields").mkdir(parents=True)
    for name in ("Common.txt", "Proof_Style.txt"):
        (rules_dir / name).write_text((ROOT / "tests" / "fixtures" / "rules_mini"
                                       / name).read_text(), encoding="utf-8")
    (rules_dir / "fields" / "mini.txt").write_text(
        '= 1. Terminology\n\n'
        'ALWAYS use "analytic" — NEVER "holomorphic".\n\n'
        'ALWAYS use "contour" — NEVER "path" when the curve is piecewise smooth.\n',
        encoding="utf-8")

    import knowledge_base.rules.compile_rules as cr

    saved = dict(cr.FIELD_DOCS)
    cr.FIELD_DOCS["mini"] = "fields/mini.txt"
    try:
        compiled = cr.compile_field("mini", rules_dir)
        assert compiled.lexicon["banned"]["holomorphic"] == "analytic", \
            "an unqualified ban is still enforced"
        assert "path" not in compiled.lexicon["banned"], \
            "a qualified ban compiles to a proposal, not an enforced pair"
        proposal = next(c for c in compiled.candidates["candidates"]
                        if c["proposed_banned"] == "path")
        assert proposal["demoted"] is True
        assert "piecewise smooth" in proposal["reason"]

        # The authored allowlist is the only way back to enforcement.
        (rules_dir / cr.ALLOWLIST_FILE).write_text(
            "allowlist:\n"
            "  - term: path\n"
            "    section: mini §1\n"
            "    reason: the qualifier describes the only kind of curve used\n",
            encoding="utf-8")
        allowed = cr.compile_field("mini", rules_dir)
        assert allowed.lexicon["banned"]["path"] == "contour"
    finally:
        cr.FIELD_DOCS.clear()
        cr.FIELD_DOCS.update(saved)


def test_the_allowlist_keeps_its_pairs_enforced_unless_facts_intervene():
    """Rouché's matters most: accent consistency is a core requirement.

    `ODE` is allowlisted and still demoted, which is the intended precedence:
    the conflicting-use check reports a fact about the documents and the
    allowlist records judgment, so facts win. Here the fact is a false
    positive — Proof Style §5.2 uses "ODE" as prose, not as a mandated phrase —
    and that cost is accepted rather than papered over."""
    ca = compile_field("complex-analysis", ROOT / "rules").lexicon["banned"]
    ode = compile_field("ordinary-differential-equations",
                        ROOT / "rules").lexicon["banned"]
    assert ca["Rouche's Theorem"] == "Rouché's Theorem"
    assert ca["outward normal derivative"] == "normal derivative"
    assert ode["PDE"] == "partial differential equation"
    assert "ODE" not in ode, "the conflicting-use check outranks the allowlist"


def test_a_qualifier_on_an_or_list_qualifies_the_whole_list():
    """`NEVER write "A" or "B" for the order.` is one ruling. Enforcing A while
    demoting B would split it on nothing but position in the list."""
    from knowledge_base.rules import compile_rules as cr
    from knowledge_base.rules import parse

    doc = parse.parse(ROOT / "rules" / "fields" / "ode.txt")
    degree = [p for p in parse.pairs(doc, "ode")[0] if "degree" in p.banned]
    assert len(degree) == 2
    assert all(cr.qualifier_of(p) == "for the order" for p in degree)

    banned = compile_field("ordinary-differential-equations",
                           ROOT / "rules").lexicon["banned"]
    assert not [b for b in banned if b.startswith("degree")]


def test_the_reported_qualifier_stops_at_the_sentence():
    """The qualifier reaches the owner in a queue entry, so reading past the
    full stop would report a restriction the author never wrote."""
    from knowledge_base.rules import compile_rules as cr
    from knowledge_base.rules import parse

    common = parse.parse(ROOT / "rules" / "Common.txt")
    iff = next(p for p in parse.pairs(common, "Common")[0] if p.banned == "iff")
    assert cr.qualifier_of(iff) == "in prose"


# ── the conflicting-use check ─────────────────────────────────────────

def test_cauchy_principal_value_survives_validation():
    """§3.3 bans "principal value" for the logarithm; §15 mandates "Cauchy
    principal value of $integral…$" in full and §17.9 mandates "principal value
    of $z^c$" as a term distinct from "principal branch of $z^c$" two lines
    above. Enforcing the pair would not merely damage those phrases — it would
    collapse two mandated terms that mean different things."""
    from knowledge_base.models.profile import load_profile
    from knowledge_base.pipeline.validate import apply_lexicon, run_rules

    profile = load_profile("complex-analysis", ROOT)
    for text in ("the Cauchy principal value of "
                 "$integral_(-infinity)^(infinity) f(x) dif x$",
                 "the principal value of $z^c$"):
        assert apply_lexicon(text, profile.lexicon.banned)[0] == text
        assert run_rules(text, profile.validators.rules)[0] == text


def test_a_conflicting_use_outranks_the_allowlist(tmp_path):
    """Facts beat judgment. An allowlist entry granted on a mistaken reading
    must not resurrect a substitution that would rewrite mandated text."""
    rules_dir = tmp_path / "rules"
    (rules_dir / "fields").mkdir(parents=True)
    for name in ("Common.txt", "Proof_Style.txt"):
        (rules_dir / name).write_text((MINI / name).read_text(), encoding="utf-8")
    (rules_dir / "fields" / "mini.txt").write_text(
        '= 1. Terminology\n\n'
        'ALWAYS use "mapping" — NEVER "transformation".\n\n'
        '= 2. Named results\n\n'
        'ALWAYS use "linear fractional transformation" in full.\n',
        encoding="utf-8")
    (rules_dir / "enforcement-allowlist.yaml").write_text(
        "allowlist:\n"
        "  - term: transformation\n"
        "    section: mini §1\n"
        "    reason: mistakenly granted\n",
        encoding="utf-8")

    import knowledge_base.rules.compile_rules as cr

    saved = dict(cr.FIELD_DOCS)
    cr.FIELD_DOCS["mini"] = "fields/mini.txt"
    try:
        compiled = cr.compile_field("mini", rules_dir)
        assert "transformation" not in compiled.lexicon["banned"]
        proposal = next(c for c in compiled.candidates["candidates"]
                        if c["proposed_banned"] == "transformation")
        assert "mandates it" in proposal["reason"]
        assert "linear fractional transformation" in proposal["reason"], \
            "the conflicting line travels with the demotion"
    finally:
        cr.FIELD_DOCS.clear()
        cr.FIELD_DOCS.update(saved)


def test_a_term_in_a_never_clause_elsewhere_is_not_a_mandate():
    """`ALWAYS write "harmonic in $D$" — NEVER "harmonic on $D$"` is a second
    prohibition, not a mandate of the banned form. Counting it as one demoted
    correct pairs on a misreading."""
    from knowledge_base.rules import compile_rules as cr

    assert [x.strip() for x in cr._mandated_parts(
        'ALWAYS write `harmonic in $D$` — NEVER `harmonic on $D$`.'
    )] == ["write `harmonic in $D$` —"]

    # CA §6 bans it; Proof Style §6.2 restates the same ban. Reading that
    # restatement as a mandate demoted the pair. It carries math, so it is a
    # notation form rather than a lexicon entry — and it is still enforced.
    compiled = compile_field("complex-analysis", ROOT / "rules")
    assert "harmonic on $D$" in {n for f in compiled.symbols["forms"] for n in f["never"]}
    assert not [c for c in compiled.candidates["candidates"]
                if c["proposed_banned"] == "harmonic on $D$" and c.get("demoted")]


def _mini_rules(tmp_path, mini_txt, ode_txt=None, allowlist=None):
    """A two-field rule tree: Common, Proof Style, and two sibling fields."""
    rules_dir = tmp_path / "rules"
    (rules_dir / "fields").mkdir(parents=True)
    for name in ("Common.txt", "Proof_Style.txt"):
        (rules_dir / name).write_text((MINI / name).read_text(), encoding="utf-8")
    (rules_dir / "fields" / "mini.txt").write_text(mini_txt, encoding="utf-8")
    if ode_txt is not None:
        (rules_dir / "fields" / "sibling.txt").write_text(ode_txt, encoding="utf-8")
    if allowlist is not None:
        (rules_dir / "enforcement-allowlist.yaml").write_text(allowlist, encoding="utf-8")
    return rules_dir


def test_a_sibling_fields_mandate_does_not_demote(tmp_path):
    """Precedence runs field > Proof Style > Common. Sibling fields sit outside
    that chain and compile into separate books, so one cannot govern the
    other's substitutions."""
    import knowledge_base.rules.compile_rules as cr

    rules_dir = _mini_rules(
        tmp_path,
        '= 1. Terminology\n\nALWAYS use "trajectory" — NEVER "path".\n',
        '= 1. Curves\n\nALWAYS "independent of path" in full.\n')

    saved = dict(cr.FIELD_DOCS)
    cr.FIELD_DOCS.update({"mini": "fields/mini.txt", "sibling": "fields/sibling.txt"})
    try:
        compiled = cr.compile_field("mini", rules_dir)
        assert compiled.lexicon["banned"]["path"] == "trajectory", \
            "a sibling field's mandate has no authority here"
    finally:
        cr.FIELD_DOCS.clear()
        cr.FIELD_DOCS.update(saved)


def test_a_governing_document_mandate_still_demotes(tmp_path):
    """The other half: Common and Proof Style do govern every field."""
    import knowledge_base.rules.compile_rules as cr

    rules_dir = _mini_rules(
        tmp_path,
        '= 1. Terminology\n\nALWAYS use "Therefore" — NEVER "Hence".\n')

    saved = dict(cr.FIELD_DOCS)
    cr.FIELD_DOCS["mini"] = "fields/mini.txt"
    try:
        compiled = cr.compile_field("mini", rules_dir)
        # Proof_Style.txt carries "ALWAYS use `Hence` for the final concluding
        # sentence." — a governing document, so the conflict stands.
        assert "Hence" not in compiled.lexicon["banned"]
        proposal = next(c for c in compiled.candidates["candidates"]
                        if c["proposed_banned"] == "Hence")
        assert "Proof_Style.txt" in proposal["reason"]
    finally:
        cr.FIELD_DOCS.clear()
        cr.FIELD_DOCS.update(saved)


def test_a_multi_always_sentence_licenses_only_its_own_segment():
    """`Label: ALWAYS value  Label: ALWAYS value` is several mandates. A term in
    one is not licensed by another, and the label introducing the next mandate
    belongs to that mandate rather than to the one it trails."""
    from knowledge_base.rules import compile_rules as cr

    sentence = ('Image of a set $A$: ALWAYS $f(A)$ '
                'Image of the entire domain: ALWAYS $"Im"(f)$')
    parts = [p.strip() for p in cr._mandated_parts(sentence)]
    assert parts == ["$f(A)$", '$"Im"(f)$']
    assert not any("entire" in p for p in parts), \
        "the lead-in to the second mandate is not mandated by the first"

    assert [x.strip() for x in cr._mandated_parts(
        'ALWAYS write `harmonic in $D$` — NEVER `harmonic on $D$`.'
    )] == ["write `harmonic in $D$` —"]


# ── failing closed applies to the substituting layer only ─────────────

def test_a_qualified_notation_form_stays_enforced():
    """A notation rule flags, it never rewrites. Demoting one loses a check and
    prevents nothing, so the fail-closed rule does not apply to it."""
    from knowledge_base.rules import compile_rules as cr
    from knowledge_base.rules import parse

    common = parse.parse(ROOT / "rules" / "Common.txt")
    sup = next(p for p in parse.pairs(common, "Common")[0] if p.banned == "$sup E$")
    assert cr.qualifier_of(sup) == "without parentheses", "it does carry a qualifier"

    forms = compile_field("complex-analysis", ROOT / "rules").symbols["forms"]
    assert "$sup E$" in {n for f in forms for n in f["never"]}


def test_a_qualified_substituting_pair_is_still_demoted():
    """The other half of the same rule: substitutions still fail closed."""
    from knowledge_base.rules import compile_rules as cr
    from knowledge_base.rules import parse

    ode = parse.parse(ROOT / "rules" / "fields" / "ode.txt")
    phase = next(p for p in parse.pairs(ode, "ode")[0] if p.banned == "phase space")
    assert not phase.is_math and cr.qualifier_of(phase)
    assert "phase space" not in compile_field(
        "ordinary-differential-equations", ROOT / "rules").lexicon["banned"]


# ── determinism and staleness ─────────────────────────────────────────

def test_compilation_is_deterministic():
    a = compile_field("complex-analysis", ROOT / "rules")
    b = compile_field("complex-analysis", ROOT / "rules")
    assert a == b


def test_check_mode_detects_staleness(tmp_path):
    import shutil

    for name in ("config.yaml",):
        shutil.copy(ROOT / name, tmp_path / name)
    shutil.copytree(ROOT / "rules", tmp_path / "rules")
    assert run(root=tmp_path, check=True) == 1, "nothing generated yet"
    assert run(root=tmp_path) == 0
    assert run(root=tmp_path, check=True) == 0, "freshly generated must be clean"

    target = outputs("complex-analysis", tmp_path)["lexicon"]
    target.write_text(target.read_text() + "\n  fake: entry\n")
    assert run(root=tmp_path, check=True) == 1, "a hand edit must be detected"


def test_generated_in_the_repo_is_current():
    """`make check` must fail when generated/ lags rules/ — that link is what
    stops the compiled artefacts from drifting away from the documents."""
    assert run(root=ROOT, check=True) == 0, "run `make rules` and commit the result"


# ── parser units ──────────────────────────────────────────────────────

def test_sentence_split_keeps_em_dash_pairs_intact():
    s = parse.sentences('ALWAYS "a" — NEVER "b". ALWAYS "c" — NEVER "d".')
    assert len(s) == 2 and s[0].startswith("ALWAYS")


def test_or_continuation_versus_explanatory_quote():
    p = parse.parse(MINI / "fields" / "mini.txt")
    confident, _ = parse.pairs(p, "mini")
    banned = {c.banned for c in confident}
    assert {"holomorphic", "regular"} <= banned
    assert "function" not in banned, "the second quote explains, it does not prohibit"
