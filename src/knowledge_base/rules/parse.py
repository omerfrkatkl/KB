"""Parsing the authored rule documents into structured rulings.

The documents are prose written for a human, but they are written to a fixed
shape: `ALWAYS X`, `NEVER Y`, `IF … THEN`. That shape is what makes three of the
four compilation targets mechanical.

What this module deliberately does **not** do is extract frame logic. Frames are
executable code with conditionals — six-way transition selection, build-time
membership checks, method-specific substructure — and no regex recovers that from
prose. `build/frames.py` is hand-written and tied to the documents by a
conformance test instead (§I-5A correction).

Two parsing rules come straight from the documents:

* **`[MOVED]` / `[MERGED]` stubs are empty.** They preserve section numbering so
  a compiler keyed on section numbers stays valid. The compiler follows the
  pointer and never parses the stub — parsing one would resurrect a rule the
  owner deliberately withdrew, such as Common §15.2's "Therefore everywhere".
* **A term that is canonical anywhere is never banned anywhere.** Section 16
  ("NEVER use "positive" to mean $x >= 0$") is a semantic ruling that looks
  exactly like a terminology pair. The global canonical set is what tells them
  apart.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

SECTION = re.compile(r"^(=+)\s+([0-9]+(?:\.[0-9]+)*)\.?\s+(.*)$")
STUB = re.compile(r"^\s*\[(MOVED|MERGED)\]")
QUOTED = re.compile(r"[\"“]([^\"”]+)[\"”]|`([^`]+)`")
MATH = re.compile(r"\$([^$]+)\$")
COMMENT = re.compile(r"^\s*//")


@dataclass
class Section:
    number: str
    title: str
    level: int
    lines: list[str] = field(default_factory=list)
    stub: bool = False

    @property
    def body(self) -> str:
        return "\n".join(self.lines)

    def paragraphs(self) -> list[str]:
        """Blank-line-separated blocks, whitespace collapsed.

        Collapsing is what lets a quoted phrase that wraps across two lines —
        `NEVER "has a derivative\\n  at $z_0$"` — be read as one string.
        """
        out, buf = [], []
        for line in self.lines:
            if line.strip():
                buf.append(line.strip())
            elif buf:
                out.append(" ".join(buf))
                buf = []
        if buf:
            out.append(" ".join(buf))
        return out


@dataclass
class Document:
    path: Path
    name: str
    sections: list[Section]

    def section(self, number: str) -> Section | None:
        return next((s for s in self.sections if s.number == number), None)

    def live(self) -> list[Section]:
        return [s for s in self.sections if not s.stub]


def parse(path: Path) -> Document:
    sections: list[Section] = []
    current: Section | None = None
    for raw in Path(path).read_text(encoding="utf-8").splitlines():
        if COMMENT.match(raw):
            continue
        hit = SECTION.match(raw)
        if hit:
            current = Section(number=hit.group(2), title=hit.group(3).strip(),
                              level=len(hit.group(1)))
            sections.append(current)
            continue
        if current is None:
            continue
        if STUB.match(raw):
            current.stub = True
        current.lines.append(raw)
    return Document(path=Path(path), name=Path(path).stem, sections=sections)


# ── clause splitting ──────────────────────────────────────────────────

@dataclass
class Clause:
    word: str      # ALWAYS | NEVER
    text: str
    before: str    # text preceding the keyword in this paragraph

KEYWORD = re.compile(r"\b(ALWAYS|NEVER)\b")


def clauses(paragraph: str) -> list[Clause]:
    """Split a paragraph at ALWAYS/NEVER, keeping order and what came before."""
    hits = list(KEYWORD.finditer(paragraph))
    out: list[Clause] = []
    for i, h in enumerate(hits):
        end = hits[i + 1].start() if i + 1 < len(hits) else len(paragraph)
        before = paragraph[:h.start()] if i == 0 else paragraph[hits[i - 1].end():h.start()]
        out.append(Clause(word=h.group(1), text=paragraph[h.end():end].strip(),
                          before=before.strip()))
    return out


def quoted(text: str) -> list[str]:
    return [(a or b).strip() for a, b in QUOTED.findall(text)]


def math_spans(text: str) -> list[str]:
    return [f"${m.strip()}$" for m in MATH.findall(text)]


# ── rulings ───────────────────────────────────────────────────────────

@dataclass(frozen=True)
class Pair:
    """One `ALWAYS X — NEVER Y` ruling, with where it came from."""
    canonical: str
    banned: str
    section: str
    document: str
    is_math: bool
    evidence: str = ""
    target_certain: bool = True   # False when the mandated form had to be guessed


# ── the confident shape ───────────────────────────────────────────────
#
# Only a pair stated in ONE sentence, with the mandate and the prohibition
# joined by an em dash, is compiled into an automatic substitution. That is the
# shape the plan describes ("77 lines are already in literal `ALWAYS X — NEVER Y`
# shape"), and it is the only shape in which the association is stated by the
# author rather than inferred by this parser.
#
# Extracting pairs across sentence boundaries — associating each NEVER with the
# nearest preceding ALWAYS — was tried first and produced confidently wrong
# rulings on the real documents: `domain -> region` from §17.1, whose sentences
# say the exact opposite; `function -> an entire function` from §5.1, where the
# second quoted word is part of the prohibition's explanation; `infinity -> the`
# from §17.1. Each of those would have become a silent, corpus-wide rewrite.
# Anything outside the confident shape is therefore reported as a candidate for
# the owner to rule on, never applied.

_ALWAYS_FIRST = re.compile(
    r"ALWAYS\b[^\"“]{0,40}?[\"“]([^\"”]+)[\"”](?:[^—]{0,120}?)—\s*NEVER\b(.{0,200})")
_TERM_FIRST = re.compile(
    r"[\"“]([^\"”]+)[\"”]\s*—\s*ALWAYS\b[^.]{0,80}\.\s*NEVER\b(.{0,200})")
_MATH_ALWAYS_FIRST = re.compile(
    r"ALWAYS\b[^$]{0,40}?(\$[^$]+\$)(?:[^—]{0,120}?)—\s*NEVER\b(.{0,200})")

_SENTENCE = re.compile(r"(?<=[.;])\s+(?=[A-Z\"“$])")


def sentences(paragraph: str) -> list[str]:
    return [s.strip() for s in _SENTENCE.split(paragraph) if s.strip()]


def _banned_list(tail: str, extractor) -> list[str]:
    """The prohibited forms in a NEVER clause.

    The first form is always taken. Later forms count only when joined by
    " or " — in `NEVER "entire" as a standalone adjective without "function"`
    the second quoted word explains the rule, it is not a second prohibition.
    """
    items = extractor(tail)
    if not items:
        return []
    out = [items[0]]
    cursor = tail.find(items[0]) + len(items[0])
    for nxt in items[1:]:
        at = tail.find(nxt, cursor)
        if at < 0:
            break
        joiner = tail[cursor:at]
        if re.fullmatch(r"[\"”`$\s]*,?\s*or\s*[\"“`$\s]*", joiner):
            out.append(nxt)
        else:
            break
        cursor = at + len(nxt)
    return out


def pairs(doc: Document, label: str) -> tuple[list[Pair], list[Pair]]:
    """Return (confident, candidates) for one document.

    Two tiers of confidence, both requiring the author to have stated the
    association rather than this parser to have inferred it:

    * **sentence tier** — mandate and prohibition joined by an em dash inside one
      sentence. This is the shape the plan counts.
    * **paragraph tier** — a paragraph with exactly one ALWAYS clause, where the
      first NEVER clause does not open by re-quoting the mandated term. One
      ALWAYS means there is no ambiguity about which mandate the prohibition
      belongs to; the re-quoting test is what separates a *replacement* ("ALWAYS
      "analytic" … NEVER "regular" or "holomorphic"") from a *scoping* ruling
      ("ALWAYS use "region" for … NEVER use "region" as a synonym for "domain""),
      which shares the syntax and means the opposite.

    Everything else is a candidate.
    """
    confident: list[Pair] = []
    candidates: list[Pair] = []
    for sec in doc.live():
        section = f"{label} §{sec.number}"
        for para in sec.paragraphs():
            found = []
            for sentence in sentences(para):
                found.extend(_confident_in(sentence, section, doc.name))
            if not found:
                found = _paragraph_tier(para, section, doc.name)
            confident.extend(found)
            candidates.extend(_candidates_in(para, section, doc.name))
    found = {(p.canonical, p.banned) for p in confident}
    candidates = [c for c in candidates if (c.canonical, c.banned) not in found]
    return confident, candidates


def _paragraph_tier(paragraph: str, section: str, document: str) -> list[Pair]:
    cs = clauses(paragraph)
    always = [c for c in cs if c.word == "ALWAYS"]
    nevers = [c for c in cs if c.word == "NEVER"]
    if len(always) != 1 or not nevers or cs.index(always[0]) > cs.index(nevers[0]):
        return []

    mandate, first_never = always[0], nevers[0]
    for extractor, is_math in ((quoted, False), (math_spans, True)):
        before = extractor(mandate.before)
        here = extractor(mandate.text)
        if not here and not before:
            continue
        mandated = here or [before[-1]]
        banned = _banned_list(first_never.text, extractor)
        if not banned or banned[0] == mandated[0]:
            # The prohibition re-quotes the mandated term: it constrains how that
            # term may be used, and the terms after it are the context of the
            # constraint, not replacements for it.
            continue
        return [Pair(canonical=c, banned=b, section=section, document=document,
                     is_math=is_math or "$" in c or "$" in b, evidence=paragraph,
                     target_certain=certain)
                for c, b, certain in _align(mandated, banned) if b != c]
    return []


def _align(mandated: list[str], banned: list[str]) -> list[tuple[str, str, bool]]:
    """Pair mandated forms with banned ones.

    Parallel lists pair positionally — `ALWAYS $sin(z)$, $cos(z)$ … NEVER
    $sin z$ or $cos z$` is two rulings, not one ruling repeated. When the lists
    are of different lengths the mandated form cannot be recovered by counting
    (`ALWAYS $sinh(z)$, $cosh(z)$, $tanh(z)$ … NEVER $sinh z$ or $cosh z$`), so
    the pair is marked uncertain and its message points at the section rather
    than naming a replacement that might be the wrong one.
    """
    if len(mandated) == len(banned) and len(banned) > 1:
        return [(m, b, True) for m, b in zip(mandated, banned)]
    certain = len(mandated) == 1
    return [(mandated[0], b, certain) for b in banned]


def _confident_in(sentence: str, section: str, document: str) -> list[Pair]:
    out: list[Pair] = []
    for pattern, extractor, is_math in (
        (_ALWAYS_FIRST, quoted, False),
        (_TERM_FIRST, quoted, False),
        (_MATH_ALWAYS_FIRST, math_spans, True),
    ):
        hit = pattern.search(sentence)
        if not hit:
            continue
        canonical = hit.group(1).strip()
        for banned in _banned_list(hit.group(2), extractor):
            banned = banned.strip()
            if banned and banned != canonical:
                out.append(Pair(canonical=canonical, banned=banned, section=section,
                                document=document,
                                is_math=is_math or "$" in canonical or "$" in banned,
                                evidence=sentence))
        break
    return out


def _candidates_in(paragraph: str, section: str, document: str) -> list[Pair]:
    """Everything that *looks* like a pair but is not stated as one.

    These are proposals for the owner, not rulings. They are written to
    `generated/lexicon/<field>.candidates.yaml` and worked in WP1.7.
    """
    found: list[Pair] = []
    pending: str | None = None
    pending_math: str | None = None
    for c in clauses(paragraph):
        qs, ms = quoted(c.text), math_spans(c.text)
        if c.word == "ALWAYS":
            before_q, before_m = quoted(c.before), math_spans(c.before)
            pending = qs[0] if qs else (before_q[-1] if before_q else None)
            pending_math = ms[0] if ms else (before_m[-1] if before_m else None)
            continue
        if pending and qs:
            for variant in qs:
                found.append(Pair(canonical=pending, banned=variant, section=section,
                                  document=document,
                                  is_math="$" in pending or "$" in variant,
                                  evidence=paragraph))
        elif pending_math and ms:
            for variant in ms:
                found.append(Pair(canonical=pending_math, banned=variant, section=section,
                                  document=document, is_math=True, evidence=paragraph))
    return found


def comma_list(section: Section) -> list[str]:
    """The indented comma-separated list a section like Common §13 carries."""
    text = " ".join(line.strip() for line in section.lines
                    if line.startswith("  ") and line.strip())
    return [t.strip(" .") for t in text.split(",") if t.strip(" .")]
