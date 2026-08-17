"""Canonical form and hashing (§I-4).

The canonical form is what makes "the same fact, captured twice" detectable. It
is computed per slot and concatenated with the type tag:

  1. substitute canonical terms via the lexicon (longest-match, word-boundary,
     case-folded) in prose runs;
  2. lowercase prose outside math;
  3. collapse whitespace;
  4. math runs: strip internal spaces and apply a small alias table;
  5. sha256.

**Step 4 is textual normalisation only.** Symbolic equivalence is out of scope
and is documented as such here rather than half-attempted: `$z^2 - 1$` and
`$(z-1)(z+1)$` are not the same string and this module will never say they are.
Treating that as a bug would lead to a CAS in the dedup path, which is a far
larger commitment than the problem justifies — near-duplicate review catches what
this misses.
"""

from __future__ import annotations

import hashlib
import re

from knowledge_base.models.item import Item
from knowledge_base.models.profile import Lexicon

MATH_RUN = re.compile(r"\$([^$]*)\$")
WHITESPACE = re.compile(r"\s+")

# Textual synonyms only — same rendering, different spelling. Maintained here,
# per §I-4, and deliberately short.
MATH_ALIASES = {
    "\\cdot": "dot",
    "\\times": "times",
    "\\leq": "<=",
    "\\geq": ">=",
    "\\neq": "!=",
    "\\subseteq": "subset.eq",
    "\\emptyset": "emptyset",
    "\\infty": "infinity",
    "\\to": "->",
    "\\Rightarrow": "=>",
    "dots.h": "dots",
    "dots.c": "dots",
    "inter": "sect",
}

# The statement slots that identify an item, per §I-4's dedup comparison.
STATEMENT_SLOTS = ("conclusion", "hypotheses", "body", "term", "citation_form",
                   "witness", "witness_properties")


def normalise_math(expression: str) -> str:
    text = expression
    for source, target in sorted(MATH_ALIASES.items(), key=lambda kv: -len(kv[0])):
        text = text.replace(source, target)
    return re.sub(r"\s+", "", text)


def canonical_text(text: str, lexicon: Lexicon) -> str:
    parts = MATH_RUN.split(text)
    # `split` on a capturing group interleaves: prose, math, prose, math, …
    out = []
    for index, part in enumerate(parts):
        if index % 2:
            out.append(f"${normalise_math(part)}$")
        else:
            out.append(_prose(part, lexicon))
    return WHITESPACE.sub(" ", "".join(out)).strip()


def _prose(text: str, lexicon: Lexicon) -> str:
    lowered = text.lower()
    for variant in sorted(lexicon.banned, key=len, reverse=True):
        pattern = re.compile(_boundary(variant), re.IGNORECASE)
        lowered = pattern.sub(lexicon.banned[variant].lower(), lowered)
    return lowered


def _boundary(term: str) -> str:
    escaped = re.escape(term)
    left = r"\b" if term[:1].isalnum() else ""
    right = r"\b" if term[-1:].isalnum() else ""
    return f"{left}{escaped}{right}"


def statement_of(item: Item) -> str:
    """The identifying text of an item: its statement slots, in a fixed order."""
    parts = [item.type.value]
    for slot in STATEMENT_SLOTS:
        value = item.slots.get(slot)
        if isinstance(value, str):
            parts.append(value)
        elif isinstance(value, list):
            parts.extend(v for v in value if isinstance(v, str))
    return " ".join(parts)


def canonical_form(item: Item, lexicon: Lexicon) -> str:
    return canonical_text(statement_of(item), lexicon)


def canonical_hash(item: Item, lexicon: Lexicon) -> str:
    return hashlib.sha256(canonical_form(item, lexicon).encode("utf-8")).hexdigest()


def normalised_statement(item: Item, lexicon: Lexicon) -> str:
    """The text near-duplicate scoring compares — statement slots only, never
    proofs. Two sources stating one theorem differently proved are one item."""
    slots = ("conclusion", "hypotheses") if item.slots.get("conclusion") else ("body",)
    parts = []
    for slot in slots:
        value = item.slots.get(slot)
        if isinstance(value, str):
            parts.append(value)
        elif isinstance(value, list):
            parts.extend(v for v in value if isinstance(v, str))
    if not parts:
        parts = [statement_of(item)]
    return canonical_text(" ".join(parts), lexicon)
