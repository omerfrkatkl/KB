"""frames.py — Proof_Style.txt and Common.txt §21, implemented in the renderer.

**Every sentence the book contains is composed here.** No model output is ever
printed; the model fills typed slots and this file turns slots into prose. That
separation is the reason the system exists, and it is what makes structural and
terminological consistency exact rather than approximate across a corpus that
grows for decades.

This file is hand-written, not generated (§I-5A correction). Frame logic is
executable code with conditionals — six-way transition selection, build-time
membership checks, method-specific substructure — and no regex extracts that
from prose, while generating it with a model at build time would reintroduce
exactly the nondeterminism the architecture removes. The deterministic link back
to the documents is `tests/test_frames_conformance.py`, which reads the literal
mandated strings out of `rules/` and asserts this module emits them. A rule
change therefore fails the build until frames is updated.

Rulings wired in:
  A16  a citation resolves to the target's NAME, else its `citation_form`.
       Never a number (§3.4).
  A17  Proof Style §3.2's six-way transition selection. Common §15.2 is deleted.
  A18  the token "we" appears nowhere; structural openings are imperative.
  A19  `$(=>)$` / `$(arrow.l.double)$`, compiler-verified.
  A20  justification presence is computed at BUILD TIME from store membership:
       in the document -> justify; absent -> no justification; identical to the
       immediately preceding step -> omitted (§2).
  A21  `citation_form` is always populated, so composing a citation from
       hypotheses and conclusion is a fallback that signals a schema violation.
  A22  "Then" for pure algebra and computation steps.

Placement (§2.1): `by the [Name]` and `by the fact that [...]` are TERMINAL;
`Since [reason], [statement].` is the only initial form.
Closings (§3.3): `Hence …` / `In all cases, …` / `By induction, … for all $n in NN$.`
"""

from __future__ import annotations

# ── A18: imperative structural openings (no "we") ──────────────────────
OPENING = {
    "direct":           None,                       # opens with Let/Assume (§4.1)
    "computation":      None,
    "contradiction":    "Suppose that {setup}.",     # §4.2
    "contrapositive":   "Prove the contrapositive. Assume that {setup}.",  # §4.6
    "induction":        "Proceed by induction on {setup}.",                # §4.4
    "strong-induction": "Proceed by strong induction on {setup}.",
    "construction":     "Construct {setup} explicitly.",                   # §4.7
    "cases":            "Consider {k} cases.",                             # §4.3
    "iff-pair":         None,                        # §4.5: the arrows carry it
    "uniqueness-pair":  None,                        # §4.7: (i)/(ii) carry it
    "double-inclusion": None,                        # the inclusions carry it
    "verify-criteria":  "Verify each condition of {definition}.",
}

CLOSING = {  # §3.3
    "cases":            "In all cases, {c}.",
    "induction":        "By induction, {c} for all $n in NN$.",
    "strong-induction": "By induction, {c} for all $n in NN$.",
}
CLOSING_DEFAULT = "Hence {c}."

# §4.5 / A19, compiler-verified. `$<=$` renders as ≤ and is never an arrow.
FORWARD_ARROW = "$(=>)$"
BACKWARD_ARROW = "$(arrow.l.double)$"
# The set-inclusion analogue, using the delimiters Common §2.1 mandates.
SUBSET_ARROW = "$(subset.eq)$"
SUPERSET_ARROW = "$(supset.eq)$"

SUFFICIENCY = "It is enough to show that {s}."

# Common §21.4 — the only two frames a counterexample may take.
CONVERSE_FRAME = "The converse of {result} is false: {witness} {properties}."
NECESSITY_FRAME = "Hypothesis {hypothesis} in {result} is necessary: {witness} {properties}."


def _join(parts) -> str:
    """Common §21.2: "A and B" for two, "A, B, and C" for three or more."""
    parts = list(parts)
    if not parts:
        return ""
    if len(parts) == 1:
        return parts[0]
    if len(parts) == 2:
        return f"{parts[0]} and {parts[1]}"
    return ", ".join(parts[:-1]) + f", and {parts[-1]}"


def _cap(s: str) -> str:
    return s[0].upper() + s[1:] if s else s


def _the(name: str) -> str:
    """§2.1 `by the [Name]`, with the article dropped for possessive and
    proper-name results — the same test Common §21.1 applies to definitions.
    "by the Cauchy Integral Formula", but "by Liouville's Theorem"."""
    first = name.split(" ", 1)[0]
    if first.endswith("'s") or first.endswith("’s"):
        return name
    return f"the {name}"


class Doc:
    """Build-time view of the store: what is IN this document (A20)."""

    def __init__(self, items_by_id, included_ids):
        self.items = items_by_id
        self.included = set(included_ids)

    def name_of(self, ulid):
        it = self.items.get(ulid)
        if not it:
            return None
        return it.get("title") or (it.get("slots") or {}).get("name")

    def content_of(self, ulid):
        """§2.1: the citation form, which every result carries (A21).

        The hypotheses-and-conclusion composition below is a fallback that
        §2.1 explicitly names as indicating a missing citation form. It exists so
        a build never emits a dangling "by the fact that", not because it is
        acceptable output.
        """
        it = self.items.get(ulid)
        if not it:
            return None
        s = it.get("slots", {})
        if s.get("citation_form"):
            return s["citation_form"]
        if s.get("hypotheses"):
            return f"if {_join(s['hypotheses'])}, then {s['conclusion']}"
        return s.get("conclusion") or s.get("body")

    def has(self, ulid):
        return ulid in self.included


def justification(j, doc: Doc):
    """Return (text, position) with position in {'terminal', 'initial', 'none'}."""
    kind = j["kind"]

    if kind == "by-hypothesis":
        return "by hypothesis", "terminal"
    if kind == "by-inductive-hypothesis":
        return "by the inductive hypothesis", "terminal"
    if kind == "by-computation":
        return "by direct computation", "terminal"

    if kind == "by-previous-step":
        # §2.1: `[Statement], since [content].` or `Since [content], [Statement].`
        return (f"since {j['content']}", "terminal") if j.get("content") else (None, "none")

    if kind == "by-definition":
        ref = j.get("ref")
        if ref and doc.has(ref):
            return f"by the definition of {j['term']}", "terminal"
        return None, "none"                                    # A20

    if kind in ("by-ref", "by-fact"):
        ref = j.get("ref")
        if ref and doc.has(ref):                               # A16 + A20
            name = doc.name_of(ref)
            if name:
                return f"by {_the(name)}", "terminal"
            return f"by the fact that {doc.content_of(ref)}", "terminal"
        # A20: a fact absent from the document carries no justification. The
        # proof gains one automatically once that result is ingested.
        return None, "none"

    return None, "none"


def transition(j, justified: bool) -> str:
    """§3.2 — chosen from the justification kind, never guessed from prose."""
    if j.get("transition"):        # Note that / Similarly / Moreover
        return j["transition"]
    kind = j["kind"]
    if kind in ("by-ref", "by-fact", "by-definition") and justified:
        return "Therefore"         # a theorem, definition, or named fact applied
    if kind == "by-mechanical":
        return "This gives"        # an operation applied to both sides
    return "Then"                  # pure algebra or computation (A22)


def render_steps(steps, doc: Doc) -> str:
    out, previous = [], None
    for st in steps:
        j = st["justification"]
        text, position = justification(j, doc)
        if text is not None and text == previous:
            # §2: never repeat an identical justification in the immediately
            # following step. The reader sees the pattern.
            text, position = None, "none"
        elif text is not None:
            previous = text
        else:
            previous = None

        claim = st["claim"]
        word = transition(j, text is not None)
        if position == "terminal" and text:
            out.append(f"{word} {claim}, {text}.")
        elif position == "initial" and text:
            out.append(f"{_cap(text)}, {claim}.")
        else:
            out.append(f"{word} {claim}.")
    return " ".join(out)


def _block(block, doc: Doc, marker: str, closing: str) -> str:
    """One labelled half of a two-part proof.

    A half may legitimately be a bare dismissal — the observed proof of
    `IJ = I ∩ J` closes one inclusion with "always true" and no steps.
    """
    steps = render_steps(block.get("steps") or [], doc)
    conclusion = block.get("conclusion")
    if not steps:
        return f"{marker} {_cap(conclusion)}." if conclusion else marker
    tail = closing.format(c=conclusion) if conclusion else ""
    return f"{marker} {steps} {tail}".strip()


def _opening(pf, parent) -> list[str]:
    parts: list[str] = []
    template = OPENING.get(pf["method"])
    if template:
        parts.append(template.format(setup=pf.get("setup") or "",
                                     k=len(pf.get("cases") or []),
                                     definition=pf.get("definition") or ""))
    elif pf.get("setup"):
        if pf.get("setup_form") == "sufficiency":
            parts.append(SUFFICIENCY.format(s=pf["setup"]))
        else:
            # §3.1 / Common §15.1: "Assume that" accepts a condition about an
            # object that already exists. "Let" introduces one; that belongs to
            # the setup text itself, which the extractor transcribed.
            parts.append(f"Assume that {pf['setup']}.")
    elif parent and (parent.get("slots") or {}).get("hypotheses"):
        parts.append(f"Assume that {_join(parent['slots']['hypotheses'])}.")
    return parts


def render_proof(pf, doc: Doc, parent=None) -> str:
    method = pf["method"]
    parts = _opening(pf, parent)
    conclusion = pf.get("conclusion") or ""

    if method == "iff-pair":                                        # §4.5
        parts.append(_block(pf["forward"], doc, FORWARD_ARROW, "Therefore {c}."))
        parts.append(_block(pf["backward"], doc, BACKWARD_ARROW, CLOSING_DEFAULT))
        if not (pf["backward"] or {}).get("conclusion"):
            parts.append(CLOSING_DEFAULT.format(c=conclusion))
        return " ".join(p for p in parts if p)

    if method == "double-inclusion":
        parts.append(_block(pf["subset"], doc, SUBSET_ARROW, "Therefore {c}."))
        parts.append(_block(pf["superset"], doc, SUPERSET_ARROW, "Therefore {c}."))
        parts.append(CLOSING_DEFAULT.format(c=conclusion))
        return " ".join(p for p in parts if p)

    if method == "uniqueness-pair":                                 # §4.7
        parts.append(_block(pf["existence"], doc, "*(i)* Existence.", "Therefore {c}."))
        parts.append(_block(pf["uniqueness"], doc, "*(ii)* Uniqueness.", CLOSING_DEFAULT))
        if not (pf["uniqueness"] or {}).get("conclusion"):
            parts.append(CLOSING_DEFAULT.format(c=conclusion))
        return " ".join(p for p in parts if p)

    if method == "verify-criteria":
        # Completeness of the list is the proof, so every criterion is labelled
        # and none may be elided. Labels are §4.8's (i)/(ii)/(iii).
        for i, criterion in enumerate(pf["criteria"], 1):
            marker = f"*({_roman(i)})* {_cap(criterion['name'])}."
            parts.append(_block(criterion, doc, marker, "Therefore {c}."))
        parts.append(CLOSING_DEFAULT.format(c=conclusion))
        return " ".join(p for p in parts if p)

    if method == "cases":                                           # §4.3
        if pf.get("steps"):
            parts.append(render_steps(pf["steps"], doc))
        for i, case in enumerate(pf["cases"], 1):
            marker = f"*Case {i}:* {case['condition']}."
            parts.append(_block(case, doc, marker, "Therefore {c}."))
        parts.append(CLOSING["cases"].format(c=conclusion))
        return " ".join(p for p in parts if p)

    if method in ("induction", "strong-induction"):                 # §4.4
        parts.append(_block(pf["base"], doc, "*Base case:*", "Therefore {c}."))
        inductive = pf["inductive"]
        marker = f"*Inductive step:* Assume that {inductive['hypothesis']}."
        parts.append(_block(inductive, doc, marker, "Therefore {c}."))
        parts.append(CLOSING[method].format(c=conclusion))
        return " ".join(p for p in parts if p)

    parts.append(render_steps(pf.get("steps") or [], doc))
    if method == "contradiction":                                   # §4.2
        # ALWAYS name what is contradicted; "This is a contradiction." alone is
        # forbidden, which is why `contradicts` is a required slot.
        parts.append(f"This contradicts {pf['contradicts']}.")
    parts.append(CLOSING_DEFAULT.format(c=conclusion))
    return " ".join(p for p in parts if p)


def _roman(n: int) -> str:
    return ("i", "ii", "iii", "iv", "v", "vi", "vii", "viii", "ix", "x")[n - 1] \
        if 1 <= n <= 10 else str(n)


# ── statement frames (Common §21) ─────────────────────────────────────

def definition(item) -> str:
    """Common §21.1 — two forms, chosen by what is being defined."""
    s = item["slots"]
    context = f"Let {s['context']}. " if s.get("context") else ""
    term = f"*{s['term']}*"
    if s.get("form") == "predicate":
        scope = f" {s['scope']}" if s.get("scope") else ""
        return f"{context}{s['subject']} is {term}{scope} if {s['body']}."
    article = s.get("article", "a")
    lead = f"{_cap(article)} {term}" if article != "none" else _cap(term)
    return f"{context}{lead} is {s['body']}."


def statement(item) -> str:
    """Common §21.2 — theorem, lemma, proposition, corollary, axiom."""
    s = item["slots"]
    if s.get("hypotheses"):
        return f"Assume that {_join(s['hypotheses'])}. Then {s['conclusion']}."
    return f"{_cap(s['conclusion'])}."


def claim_body(item) -> str:
    return f"{_cap(item['slots']['body'])}."


def counterexample(item, doc: Doc) -> str:
    """Common §21.4 — admitted only for a false converse or a necessary
    hypothesis, and rendered by one of exactly two frames."""
    s = item["slots"]
    target = doc.name_of(s["target"]) or doc.content_of(s["target"]) or "the result"
    if s["establishes"] == "converse-false":
        return CONVERSE_FRAME.format(result=target, witness=s["witness"],
                                     properties=s["witness_properties"])
    return NECESSITY_FRAME.format(hypothesis=s["hypothesis"], result=target,
                                  witness=s["witness"], properties=s["witness_properties"])


PROSE_TYPES = {"axiom", "notation", "remark"}


def body_of(item, doc: Doc) -> str:
    """The rendered body of any item, dispatched on its type."""
    t = item["type"]
    if t == "definition":
        return definition(item)
    if t == "counterexample":
        return counterexample(item, doc)
    if t == "claim":
        return claim_body(item)
    if t in PROSE_TYPES:
        return f"{_cap(item['slots']['body'])}."
    return statement(item)
