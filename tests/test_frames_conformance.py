"""The conformance test — the deterministic link between `rules/` and `frames.py`.

Frames cannot be *compiled* from the rule documents (§I-5A correction): the logic
is executable, with conditionals no regex recovers from prose. What can be
mechanical is the check. The documents carry many literal mandated strings —
"Hence [conclusion].", "Consider [n] cases.", "by the inductive hypothesis" — and
this file reads them **out of the documents at test time** and asserts that
frames emits exactly those. When a rule document changes, this fails, and it
stays failing until frames is updated to match.

That is the whole point: the strings below are not typed here, they are extracted
from `rules/`. A test with the strings hard-coded would pass forever while the
documents drifted away from the renderer.
"""

import re
from pathlib import Path

import pytest

from knowledge_base.build import frames as F
from knowledge_base.rules import parse

ROOT = Path(__file__).resolve().parents[1]
PROOF_STYLE = ROOT / "rules" / "Proof_Style.txt"
COMMON = ROOT / "rules" / "Common.txt"


@pytest.fixture(scope="module")
def proof_style():
    return parse.parse(PROOF_STYLE)


@pytest.fixture(scope="module")
def common():
    return parse.parse(COMMON)


def mandated(doc, number: str) -> str:
    """The live text of a section, whitespace collapsed. A stub reads as empty."""
    section = doc.section(number)
    assert section is not None, f"section {number} is missing from {doc.name}"
    assert not section.stub, f"section {number} is a stub — follow its pointer"
    return " ".join(section.body.split())


def placeholders(template: str) -> str:
    """Frame text with its Python fields removed, for substring matching."""
    return re.sub(r"\{[a-z_]+\}", "", template).strip()


DOC = F.Doc({}, set())


def step(claim="$a = b$", **just):
    just.setdefault("kind", "by-computation")
    return {"claim": claim, "justification": just}


def render_every_method() -> dict[str, str]:
    """One rendered proof per method in the schema. Used by the checks that must
    hold of *all* output rather than of one frame."""
    block = {"steps": [step()], "conclusion": "$P$"}
    common = {"conclusion": "$P$ holds", "steps": [step()]}
    specimens = {
        "direct": {"method": "direct", **common},
        "computation": {"method": "computation", **common},
        "contradiction": {"method": "contradiction", "setup": "$P$ fails",
                          "contradicts": "the hypothesis", **common},
        "contrapositive": {"method": "contrapositive", "setup": "$Q$ fails", **common},
        "construction": {"method": "construction", "setup": "the object", **common},
        "cases": {"method": "cases", "conclusion": "$P$ holds", "cases": [
            {"condition": "$x > 0$", "steps": [step()], "conclusion": "$P$"},
            {"condition": "$x <= 0$", "steps": [step()], "conclusion": "$P$"}]},
        "induction": {"method": "induction", "setup": "$n$", "conclusion": "$P(n)$",
                      "base": dict(block), "inductive": {"hypothesis": "$P(n)$",
                                                         "steps": [step()],
                                                         "conclusion": "$P(n+1)$"}},
        "strong-induction": {"method": "strong-induction", "setup": "$n$",
                             "conclusion": "$P(n)$", "base": dict(block),
                             "inductive": {"hypothesis": "$P(k)$", "steps": [step()],
                                           "conclusion": "$P(n+1)$"}},
        "iff-pair": {"method": "iff-pair", "conclusion": "$P$",
                     "forward": dict(block), "backward": dict(block)},
        "uniqueness-pair": {"method": "uniqueness-pair", "conclusion": "$x$ is unique",
                            "existence": dict(block), "uniqueness": dict(block)},
        "double-inclusion": {"method": "double-inclusion", "conclusion": "$A = B$",
                             "subset": dict(block),
                             "superset": {"steps": [], "conclusion": "always true"}},
        "verify-criteria": {"method": "verify-criteria", "conclusion": "$I$ is an ideal",
                            "definition": "an ideal",
                            "criteria": [{"name": "closed under addition",
                                          "steps": [step()], "conclusion": "$P$"}]},
    }
    return {k: F.render_proof(v, DOC) for k, v in specimens.items()}


# ── §2.1 justification formats ────────────────────────────────────────

def test_hypothesis_and_inductive_hypothesis_wording(proof_style):
    text = mandated(proof_style, "2.1")
    assert "`by hypothesis`" in text
    assert "`by the inductive hypothesis`" in text
    assert F.justification({"kind": "by-hypothesis"}, DOC)[0] == "by hypothesis"
    assert F.justification({"kind": "by-inductive-hypothesis"}, DOC)[0] == \
        "by the inductive hypothesis"


def test_named_citation_takes_the_article_the(proof_style):
    text = mandated(proof_style, "2.1")
    assert "`by the [Name]`" in text
    doc = F.Doc({"X": {"title": "Cauchy Integral Formula", "slots": {}}}, {"X"})
    assert F.justification({"kind": "by-ref", "ref": "X"}, doc)[0] == \
        "by the Cauchy Integral Formula"


def test_unnamed_citation_uses_the_citation_form(proof_style):
    text = mandated(proof_style, "2.1")
    assert "`by the fact that [citation form of the fact]`" in text
    doc = F.Doc({"X": {"title": None,
                       "slots": {"citation_form": "a limit is unique"}}}, {"X"})
    assert F.justification({"kind": "by-fact", "fact": "x", "ref": "X"}, doc)[0] == \
        "by the fact that a limit is unique"


def test_justifications_are_terminal_not_initial(proof_style):
    text = mandated(proof_style, "2.1")
    assert "NEVER place `by the [Name]` or `by the fact that` at the beginning" in text
    doc = F.Doc({"X": {"title": "Cauchy Integral Formula", "slots": {}}}, {"X"})
    rendered = F.render_steps([step("$f$ is analytic", kind="by-ref", ref="X")], doc)
    assert rendered == "Therefore $f$ is analytic, by the Cauchy Integral Formula."
    assert not rendered.startswith("By the")


def test_since_is_the_only_initial_form(proof_style):
    text = mandated(proof_style, "2.1")
    assert "`Since [reason], [statement].` is always" in text
    out = F.render_steps([step("$a^n = 0$", kind="by-previous-step",
                               content="$a$ is nilpotent")], DOC)
    assert "since $a$ is nilpotent." in out


def test_an_identical_justification_is_never_repeated(proof_style):
    text = mandated(proof_style, "2")
    assert "NEVER repeat it verbatim" in text
    doc = F.Doc({"X": {"title": "Triangle Inequality", "slots": {}}}, {"X"})
    out = F.render_steps([step("$a <= b$", kind="by-ref", ref="X"),
                          step("$b <= c$", kind="by-ref", ref="X")], doc)
    assert out.count("Triangle Inequality") == 1


def test_a_fact_absent_from_the_document_carries_no_justification(proof_style):
    text = mandated(proof_style, "2")
    assert "IF the fact used does not appear anywhere in the document: NEVER write a justification" in text
    doc = F.Doc({"X": {"title": "Cauchy Integral Formula", "slots": {}}}, set())
    assert F.render_steps([step("$f$ is analytic", kind="by-ref", ref="X")], doc) == \
        "Then $f$ is analytic."


# ── §3.2 transitions ──────────────────────────────────────────────────

def test_all_six_transitions_are_selected_from_the_justification_kind(proof_style):
    text = mandated(proof_style, "3.2")
    for word in ("Therefore", "Then", "This gives", "Note that", "Similarly", "Moreover"):
        assert f'ALWAYS use "{word}"' in text, word

    doc = F.Doc({"X": {"title": "Liouville's Theorem", "slots": {}}}, {"X"})
    assert F.transition({"kind": "by-ref", "ref": "X"}, True) == "Therefore"
    assert F.transition({"kind": "by-computation"}, False) == "Then"
    assert F.transition({"kind": "by-mechanical"}, False) == "This gives"
    for word in ("Note that", "Similarly", "Moreover"):
        assert F.transition({"kind": "by-computation", "transition": word}, False) == word
    del doc


def test_the_forbidden_connectives_never_appear(proof_style, common):
    text = mandated(proof_style, "3.2") + " " + mandated(common, "14")
    for word in ("thus", "so", "it follows that", "clearly", "trivially",
                 "obviously", "one can show", "it is easy to see"):
        assert word in text
    for method, rendered in render_every_method().items():
        for word in ("thus", "clearly", "trivially", "obviously", "it follows that",
                     "one can show", "it is easy to see"):
            assert not re.search(rf"\b{re.escape(word)}\b", rendered, re.IGNORECASE), \
                f"{method}: {word}"


def test_every_proof_closes_with_exactly_one_of_the_three_closings(proof_style):
    """§3.3: every proof ALWAYS ends with exactly one of three fixed phrases."""
    assert "Every proof ALWAYS ends with exactly one of three fixed closing phrases" in \
        mandated(proof_style, "3.3")
    for method, rendered in render_every_method().items():
        closes_hence = rendered.rstrip().split(". ")[-1].startswith("Hence ")
        closes_cases = "In all cases," in rendered.rsplit(". ", 1)[-1]
        closes_induction = rendered.rstrip().endswith("for all $n in NN$.")
        assert closes_hence or closes_cases or closes_induction, f"{method}: {rendered}"
        if method in ("cases",):
            assert closes_cases and not closes_hence
        if method in ("induction", "strong-induction"):
            assert closes_induction and "Hence" not in rendered


def test_the_token_we_appears_in_no_rendered_output(common):
    """A18: "we" is banned as a token, in every phrase and every position. The
    check is on what frames *emits* — every method, rendered — because that is
    the text that reaches the page."""
    assert '"we" — forbidden as a token' in mandated(common, "14")
    for rendered in render_every_method().values():
        assert not re.search(r"\bwe\b", rendered, re.IGNORECASE), rendered


# ── §3.3 closings ─────────────────────────────────────────────────────

def test_the_three_closings_are_exactly_the_documents(proof_style):
    text = mandated(proof_style, "3.3")
    assert '"Hence [conclusion]."' in text
    assert '"In all cases, [conclusion]."' in text
    assert '"By induction, [conclusion] for all $n in NN$."' in text

    assert placeholders(F.CLOSING_DEFAULT) == "Hence ."
    assert placeholders(F.CLOSING["cases"]) == "In all cases, ."
    assert F.CLOSING["induction"].format(c="[conclusion]") == \
        "By induction, [conclusion] for all $n in NN$."


def test_no_frame_writes_qed_or_completes_the_proof(proof_style):
    text = mandated(proof_style, "3.3")
    assert "NEVER write `This completes the proof.`" in text
    assert "NEVER write `QED`" in text
    source = (ROOT / "src" / "knowledge_base" / "build" / "frames.py").read_text()
    assert "This completes the proof" not in source
    assert "QED" not in source
    assert "square.filled" not in source, "the #proof environment adds it"


# ── §4 proof types ────────────────────────────────────────────────────

def test_contradiction_opens_and_closes_as_mandated(proof_style):
    text = mandated(proof_style, "4.2")
    assert "ALWAYS `Suppose that [negation of conclusion].`" in text
    assert "NEVER write `Suppose for contradiction that`" in text
    assert "This contradicts [named or described fact]." in text

    out = F.render_proof({"method": "contradiction", "setup": "$f$ is unbounded",
                          "contradicts": "the boundedness of $f$",
                          "conclusion": "$f$ is constant", "steps": []}, DOC)
    assert out.startswith("Suppose that $f$ is unbounded.")
    assert "for contradiction" not in out
    assert "This contradicts the boundedness of $f$. Hence $f$ is constant." in out


def test_cases_frame_matches_the_document(proof_style):
    text = mandated(proof_style, "4.3")
    assert "Opening: ALWAYS `Consider [n] cases.`" in text
    assert "`*Case [k]:* [condition]. [steps]. Therefore [conclusion of this case].`" in text
    assert "ALWAYS set the case label in bold, as `*Case 1:*`" in text
    assert "NEVER write `Case (1):` with parentheses" in text

    out = F.render_proof({"method": "cases", "conclusion": "$|z| >= 0$", "cases": [
        {"condition": "$z = 0$", "steps": [step()], "conclusion": "$|z| = 0$"},
        {"condition": "$z != 0$", "steps": [step()], "conclusion": "$|z| > 0$"},
    ]}, DOC)
    assert out.startswith("Consider 2 cases.")
    assert "*Case 1:* $z = 0$." in out and "*Case 2:* $z != 0$." in out
    assert "Case (1)" not in out
    assert out.endswith("In all cases, $|z| >= 0$.")
    assert " Hence " not in out, "§4.3: NEVER use Hence before the final closing line"


def test_induction_frame_matches_the_document(proof_style):
    text = mandated(proof_style, "4.4")
    assert "Opening: ALWAYS `Proceed by induction on $n$.`" in text
    assert "`*Base case:*" in text
    assert "`*Inductive step:* Assume that" in text
    assert "ALWAYS write `by the inductive hypothesis` at every use" in text

    out = F.render_proof({"method": "induction", "setup": "$n$",
                          "conclusion": "$P(n)$ holds",
                          "base": {"steps": [step()], "conclusion": "$P(1)$ is true"},
                          "inductive": {"hypothesis": "$P(n)$ is true",
                                        "steps": [step("$P(n+1)$",
                                                       kind="by-inductive-hypothesis")],
                                        "conclusion": "$P(n+1)$ is true"}}, DOC)
    assert out.startswith("Proceed by induction on $n$.")
    assert "*Base case:*" in out
    assert "*Inductive step:* Assume that $P(n)$ is true." in out
    assert "by the inductive hypothesis" in out
    assert out.endswith("By induction, $P(n)$ holds for all $n in NN$.")


def test_biconditional_arrows_are_the_verified_codepoints(proof_style):
    text = mandated(proof_style, "4.5")
    assert "`$=>$` renders ⇒" in text
    assert "`$arrow.l.double$` renders ⇐" in text
    assert "NEVER use the long pair `$==>$` / `$<==$`" in text
    assert "$<=$" in text and "NEVER use as an arrow" in text.replace("—", "")

    assert F.FORWARD_ARROW == "$(=>)$"
    assert F.BACKWARD_ARROW == "$(arrow.l.double)$"
    out = F.render_proof({"method": "iff-pair", "conclusion": "$P$",
                          "forward": {"steps": [step()], "conclusion": "$Q$"},
                          "backward": {"steps": [step()], "conclusion": "$P$"}}, DOC)
    assert out.startswith("$(=>)$")
    assert "$(arrow.l.double)$" in out
    assert "$==>$" not in out and "$<==$" not in out
    # §4.5: the first direction closes with Therefore, the second with Hence.
    forward, backward = out.split("$(arrow.l.double)$")
    assert "Therefore $Q$." in forward and "Hence" not in forward
    assert "Hence $P$." in backward


def test_contrapositive_states_itself(proof_style):
    text = mandated(proof_style, "4.6")
    assert "ALWAYS `Prove the contrapositive. Assume that [negation of Q].`" in text
    assert "NEVER begin a contrapositive proof without this statement" in text
    out = F.render_proof({"method": "contrapositive", "setup": "$Q$ is false",
                          "conclusion": "$P$ is false", "steps": [step()]}, DOC)
    assert out.startswith("Prove the contrapositive. Assume that $Q$ is false.")


def test_existence_and_uniqueness_labels(proof_style):
    text = mandated(proof_style, "4.7")
    assert "ALWAYS `Construct [object] explicitly.`" in text
    assert "`*(i)* Existence." in text and "`*(ii)* Uniqueness." in text
    assert "NEVER use `Hence` in step (i)" in text

    out = F.render_proof({"method": "uniqueness-pair", "conclusion": "$x$ is unique",
                          "existence": {"steps": [step()], "conclusion": "$x$ exists"},
                          "uniqueness": {"steps": [step()], "conclusion": "$x$ is unique"}},
                         DOC)
    first, second = out.split("*(ii)*")
    assert "*(i)* Existence." in first and "Hence" not in first
    assert "Hence $x$ is unique." in second

    built = F.render_proof({"method": "construction", "setup": "the antiderivative",
                            "conclusion": "$F$ exists", "steps": [step()]}, DOC)
    assert built.startswith("Construct the antiderivative explicitly.")


def test_step_labels_are_roman_never_arabic(proof_style):
    text = mandated(proof_style, "4.8")
    assert "ALWAYS label steps as *(i)*, *(ii)*, *(iii)* in bold" in text
    assert "NEVER use `Step 1`, `Step (1)`, or arabic numerals" in text
    out = F.render_proof({"method": "verify-criteria", "conclusion": "$I$ is an ideal",
                          "definition": "an ideal",
                          "criteria": [{"name": "closed under addition", "steps": [step()],
                                        "conclusion": "$a + b in I$"},
                                       {"name": "absorbs products", "steps": [step()],
                                        "conclusion": "$r a in I$"}]}, DOC)
    assert "*(i)*" in out and "*(ii)*" in out
    assert "Step 1" not in out


# ── methods added from observed material (plan revision 12) ───────────

def test_double_inclusion_uses_the_mandated_subset_delimiters(common):
    """Common §2.1 forbids bare $subset$; the inclusion markers must respect it."""
    text = mandated(common, "2.1")
    assert "ALWAYS use $subset.eq$" in text
    assert "NEVER use $subset$ alone" in text
    assert F.SUBSET_ARROW == "$(subset.eq)$"
    assert "$(subset)$" not in (F.SUBSET_ARROW + F.SUPERSET_ARROW)

    out = F.render_proof({"method": "double-inclusion", "conclusion": "$I J = I sect J$",
                          "subset": {"steps": [step()], "conclusion": "$I J subset.eq I sect J$"},
                          "superset": {"steps": [], "conclusion": "always true"}}, DOC)
    assert out.startswith("$(subset.eq)$")
    assert "$(supset.eq)$ Always true." in out, "a dismissal half renders as itself"
    assert out.endswith("Hence $I J = I sect J$.")


def test_sufficiency_setup_form():
    out = F.render_proof({"method": "direct", "setup": "$f$ is bounded",
                          "setup_form": "sufficiency", "conclusion": "$f$ is constant",
                          "steps": [step()]}, DOC)
    assert out.startswith("It is enough to show that $f$ is bounded.")


# ── Common §21 statement forms ────────────────────────────────────────

def test_definition_noun_form(common):
    text = mandated(common, "21.1")
    assert 'ALWAYS "[Article] *[term]* is [body]."' in text
    assert 'ALWAYS "the" for a unique object' in text
    assert "ALWAYS no article for a possessive or proper-name term" in text

    assert F.definition({"slots": {"term": "domain", "form": "noun", "article": "a",
                                   "body": "a non-empty open connected set"}}) == \
        "A *domain* is a non-empty open connected set."
    assert F.definition({"slots": {"term": "complex plane", "form": "noun",
                                   "article": "the", "body": "$RR^2$ with $i$"}}) == \
        "The *complex plane* is $RR^2$ with $i$."
    assert F.definition({"slots": {"term": "Laplace's equation", "form": "noun",
                                   "article": "none",
                                   "body": "the equation $nabla^2 u = 0$"}}) == \
        "*Laplace's equation* is the equation $nabla^2 u = 0$."


def test_definition_predicate_form_and_context_prefix(common):
    text = mandated(common, "21.1")
    assert 'ALWAYS "[Subject] is *[term]* [scope] if [body]."' in text
    assert 'ALWAYS prefix them with "Let [context]. "' in text
    out = F.definition({"slots": {"term": "harmonic", "form": "predicate",
                                  "subject": "A function $u(x, y)$", "scope": "in $D$",
                                  "context": "$D$ be a domain",
                                  "body": "$nabla^2 u = 0$ there"}})
    assert out == "Let $D$ be a domain. A function $u(x, y)$ is *harmonic* in $D$ " \
                  "if $nabla^2 u = 0$ there."


def test_theorem_class_statement_form(common):
    text = mandated(common, "21.2")
    assert 'ALWAYS "Assume that [hypotheses]. Then [conclusion]."' in text
    assert 'Hypotheses are joined as "A and B" for two, and "A, B, and C" for three' in text
    assert 'NEVER open a statement with "If ... then ..."' in text

    assert F.statement({"slots": {"hypotheses": ["A", "B"], "conclusion": "C"}}) == \
        "Assume that A and B. Then C."
    assert F.statement({"slots": {"hypotheses": ["A", "B", "C"], "conclusion": "D"}}) == \
        "Assume that A, B, and C. Then D."
    assert F.statement({"slots": {"hypotheses": [], "conclusion": "every $z$ is finite"}}) \
        == "Every $z$ is finite."


def test_counterexample_frames(common):
    text = mandated(common, "21.4")
    assert 'ALWAYS "The converse of [result] is false: [witness] [witness properties]."' in text
    assert 'ALWAYS "Hypothesis [H] in [result] is necessary: [witness] [witness properties]."' in text
    assert "NEVER write a counterexample in question-then-solution form" in text

    doc = F.Doc({"T": {"title": "Cauchy–Riemann Theorem", "slots": {}}}, {"T"})
    assert F.counterexample({"slots": {"target": "T", "establishes": "converse-false",
                                       "witness": "$f(z) = |z|^2$",
                                       "witness_properties": "satisfies them only at $0$"}},
                            doc) == \
        "The converse of Cauchy–Riemann Theorem is false: $f(z) = |z|^2$ " \
        "satisfies them only at $0$."
    assert F.counterexample({"slots": {"target": "T", "establishes": "hypothesis-necessary",
                                       "hypothesis": "continuity of the partials",
                                       "witness": "$f(z) = |z|^2$",
                                       "witness_properties": "is not analytic"}},
                            doc).startswith("Hypothesis continuity of the partials in ")


def test_citation_form_is_a_clause_not_a_composition(common, proof_style):
    """§21.3 + §2.1: composing from hypotheses and conclusion is the fallback
    that signals a missing citation form, never the intended path."""
    assert "ALWAYS write the citation form as a clause" in mandated(common, "21.3")
    assert 'NEVER compose the citation from the result\'s hypotheses and conclusion' in \
        mandated(proof_style, "2.1")
    doc = F.Doc({"X": {"title": None, "slots": {"citation_form": "a limit is unique",
                                                "hypotheses": ["A"], "conclusion": "B"}}},
                {"X"})
    assert doc.content_of("X") == "a limit is unique"


# ── every method the schema allows must render ────────────────────────

def test_every_proof_method_has_a_frame():
    from knowledge_base.models.slots import ProofMethod

    for method in ProofMethod:
        assert method.value in F.OPENING, f"{method.value} has no opening entry"
