"""`rules/` -> `generated/` (§I-5A). Run by `make rules` and `knowledge-base rules`.

Three mechanical targets, one deliberately absent:

  lexicon    <- pure-prose ALWAYS/NEVER pairs; substituted automatically
  symbols    <- notation pairs, i.e. pairs where either side carries math
  validators <- everything a regex can check on *transcribed slot content*:
                the prose pairs again (as fixes), Common §13 hyphenation,
                §14 forbidden words, §17 name abbreviations
  frames     <- NOT generated. Hand-written in build/frames.py and tied to the
                documents by a conformance test (§I-5A correction).

Precedence is applied as the documents state it — field file > Proof_Style >
Common — so a field ruling overrides a general one rather than colliding with it.

Determinism matters more than completeness here. This runs on every `make rules`
and the pre-commit hook diffs its output, so the same documents must always
produce byte-identical files: everything is sorted, and nothing depends on
dictionary insertion order or on the filesystem.

    python -m knowledge_base.rules.compile_rules            # write
    python -m knowledge_base.rules.compile_rules --check    # verify, write nothing
"""

from __future__ import annotations

import argparse
import io
import re
import sys
from dataclasses import dataclass
from pathlib import Path

from ruamel.yaml import YAML

from knowledge_base.config import ROOT, load
from knowledge_base.ops.log import get
from knowledge_base.rules import parse

log = get("rules")

HEADER = (
    "# GENERATED — do not hand-edit. Compiled from rules/ by `make rules`.\n"
    "# Fix the rule document and regenerate; the pre-commit hook enforces this.\n"
)

# Field key -> the field rule document that outranks the shared ones.
FIELD_DOCS = {
    "complex-analysis": "fields/complex-analysis.txt",
    "ordinary-differential-equations": "fields/ode.txt",
}
SHARED_DOCS = ["Common.txt", "Proof_Style.txt"]

# §I-5A assigns each document a destination, and the destination — not the
# topic — is what decides where a rule compiles to. Honouring that split is not
# tidiness: `Proof_Style.txt` is written in the same ALWAYS/NEVER shape as the
# terminology documents, but its rulings are *frame templates*. Compiling
# "ALWAYS use `Hence` for the final concluding sentence. NEVER use `Therefore`
# … as the final closing sentence." as a terminology pair would install a
# store-wide substitution of Therefore -> Hence. Proof Style reaches the system
# through hand-written frames and the conformance test that ties them to it.
DESTINATIONS = {
    "Common": {"symbols", "validators"},   # §2–§12 notation, §13/§14/§17/§18/§19
    "Proof_Style": set(),                  # frames only (§I-5A correction)
    "field": {"lexicon", "symbols", "validators"},
}

# Frame placeholders — `[conclusion]`, `*Case 1:*` — are not terminology. The
# test is applied to prose pairs only: `*` is ordinary syntax inside math, and
# `$z^*$` is a notation ruling, not a frame.
FRAME_SHAPED = re.compile(r"[\[\]*]")


# ── scoped bans: demoted to proposals ─────────────────────────────────
#
# The compiler can represent an UNCONDITIONAL pair and nothing else. A validator
# rule carries a pattern, a fix, a prose/math scope and a list of exception
# phrases; it has no way to say "only when the surrounding text is about this
# set". A rule document that scopes a ban in prose therefore compiles to a ban
# that is broader than the document states, and the substitution fires where the
# document says it must not.
#
# `except_phrases` cannot express it either. `validate._excused` requires the
# exception phrase to CONTAIN the matched term, so a bare context word such as
# "infinity" never suppresses anything — a guard written that way would look
# like protection and do nothing.
#
# Entries here are therefore routed to `<field>.candidates.yaml` and raised on
# the new-term queue for a human ruling, instead of firing automatically.
#
# This list is explicit rather than inferred, and that is deliberate. A
# heuristic on trailing qualifiers also catches `line integral` (§8),
# `degree` (ODE §1.1) and `phase space` (ODE §14.1), which are live enforced
# pairs nobody has ruled on. Demoting them as a side effect of fixing this one
# would be a silent policy change; they are reported in the setup report instead.
DEMOTED_PAIRS: dict[tuple[str, str], str] = {
    ("deleted neighborhood", "complex-analysis §7.4"):
        "§7.4 scopes the ban to $0 < |z - z_0| < R$. A neighborhood of infinity "
        "is $|z| > 1/epsilon$ (§17.1), which is not a disk, so substituting "
        '"punctured disk" there produces a false statement. The scope is prose '
        "this compiler cannot represent, so the pair awaits a ruling.",
    ("phase space", "ode §14.1"):
        "§14.1 scopes the ban by dimension, which no substitution can detect. "
        'For a system of dimension three or higher "phase space" is correct, so '
        "the pair is ruled on in review and never applied automatically.",
}


# ── failing closed on scoped bans ─────────────────────────────────────
#
# Patching pair by pair does not prevent recurrence: the next rule edit
# reintroduces the same defect silently. So the DEFAULT for a prohibition that
# carries a qualifier is a proposal, and enforcement is the exception, granted
# by an authored allowlist.
#
# The qualifier is looked for in the clause attached to the prohibition — the
# text immediately following the banned term inside the NEVER — not anywhere in
# the sentence. Scanning the whole sentence would fire on the "for" in nearly
# every ALWAYS clause, which is noise rather than caution.
#
# This over-triggers, and that is the intended direction. A false demotion costs
# one queue entry a human clears in seconds; a false enforcement corrupts the
# corpus and `relint` applies it retroactively to everything already stored.
RESTRICTIVE_QUALIFIER = re.compile(
    r"^(for|when|in|if|unless|only|alone|except|outside|within|without|"
    r"as a|to mean|with respect to)\b", re.I)

ALLOWLIST_FILE = "enforcement-allowlist.yaml"


def qualifier_of(pair: parse.Pair) -> str | None:
    """The clause the document attaches to this prohibition, if any.

    Bounded to the sentence carrying the prohibition — reading past the full
    stop swallows the next sentence and reports a qualifier the author never
    attached, which then lands in the queue entry the owner reads.

    A qualifier on an `or`-list qualifies the whole list. `NEVER write "A" or
    "B" for the order.` is one ruling, and enforcing A while demoting B would
    split it on nothing but list position.
    """
    sentence = _never_sentence(pair)
    if sentence is None:
        return None
    own = _tail_after(sentence, pair.banned)
    if own and RESTRICTIVE_QUALIFIER.match(own):
        return own
    if own and re.match(r"^or\b", own, re.I):
        siblings = parse.quoted(sentence) or parse.math_spans(sentence)
        if siblings:
            shared = _tail_after(sentence, siblings[-1])
            if shared and RESTRICTIVE_QUALIFIER.match(shared):
                return shared
    return None


def _never_sentence(pair: parse.Pair) -> str | None:
    for sentence in parse.sentences(pair.evidence):
        if "NEVER" in sentence and pair.banned in sentence:
            return sentence
    return pair.evidence if pair.banned in pair.evidence else None


def _tail_after(sentence: str, term: str) -> str:
    hit = re.search(re.escape(term) + r"[\"”]?\s*(.{0,90})", sentence)
    return hit.group(1).strip(" .,\"”") if hit else ""


def load_allowlist(rules_dir: Path) -> dict[tuple[str, str], str]:
    path = Path(rules_dir) / ALLOWLIST_FILE
    if not path.exists():
        return {}
    raw = _yaml().load(path.read_text(encoding="utf-8")) or {}
    return {(str(e["term"]), str(e["section"])): " ".join(str(e["reason"]).split())
            for e in (raw.get("allowlist") or [])}


# ── the conflicting-use check ─────────────────────────────────────────
#
# Before a pair may be enforced, every other occurrence of the banned term in
# `rules/` is examined. If the term appears in an ALWAYS sentence somewhere else
# — that is, inside a phrase the documents *mandate* — the ban contradicts a
# mandate and the pair is demoted.
#
# **The allowlist cannot override this.** The allowlist records judgment; this
# check records facts stated in the documents, and facts win. An entry granted
# on a mistaken reading cannot resurrect a substitution that would rewrite
# mandated text.
#
# What it catches, on the real documents: `principal value`, banned by §3.3 for
# the logarithm while §15 mandates "Cauchy principal value of …" and §17.9
# mandates "principal value of $z^c$" as a term distinct from "principal branch
# of $z^c$" two lines above — so enforcing it would collapse two mandated terms
# that mean different things.
#
# What it cannot catch, and this is the limit worth remembering: a conflict the
# documents do not state. `line integral` occurs exactly once in all of rules/,
# on the line that bans it; the Green's theorem use that makes the ban wrong is
# a fact about the mathematics, not a fact in the text. This check finds
# contradictions the documents contain, never the ones they omit.


def _document_sentences(rules_dir: Path, field_doc: str | None) -> list[tuple[str, str]]:
    """(file label, sentence) for every sentence in the documents that GOVERN
    this field: `Common.txt`, `Proof_Style.txt`, and the field's own file.

    A sibling field's document is never consulted. Precedence runs
    field file > Proof_Style > Common, and sibling fields sit outside that
    chain entirely — they compile into separate books, so a Complex Analysis
    mandate has no authority over an Ordinary Differential Equations
    substitution. Searching every file made ODE's `piecewise smooth` and `path`
    collide with Complex Analysis §7.1 and §17.4, which govern neither.
    """
    paths = [Path(rules_dir) / name for name in SHARED_DOCS]
    if field_doc:
        paths.append(Path(rules_dir) / field_doc)

    out: list[tuple[str, str]] = []
    for path in paths:
        if not path.exists():
            continue
        doc = parse.parse(path)
        for section in doc.sections:
            for paragraph in section.paragraphs():
                for sentence in parse.sentences(paragraph):
                    out.append((f"{path.name} §{section.number}", sentence))
    return out


def conflicting_use(pair: parse.Pair,
                    sentences: list[tuple[str, str]]) -> tuple[str, str] | None:
    """(where, sentence) of a mandate that uses the banned term, if one exists."""
    own = " ".join(pair.evidence.split())
    pattern = (re.compile(re.escape(pair.banned)) if pair.is_math
               else re.compile(_word_pattern(pair.banned), re.IGNORECASE))
    for where, sentence in sentences:
        flat = " ".join(sentence.split())
        if "ALWAYS" not in flat or not pattern.search(flat):
            continue
        if flat in own or own in flat:
            continue          # the pair's own ruling, not a conflicting one
        if any(pattern.search(part) for part in _mandated_parts(flat)):
            return where, flat
    return None


def _mandated_parts(sentence: str) -> list[str]:
    """Every span a sentence mandates: one per ALWAYS, ending at the next
    ALWAYS or NEVER, whichever comes first.

    Three bounds, each earning its place on a real false positive.

    *After ALWAYS* — a term before the keyword is lead-in, not mandated text.
    Common §4.2's "Image of the entire domain: ALWAYS $\"Im\"(f)$" mandates a
    symbol; "entire" and "domain" there are ordinary English.

    *Before NEVER* — a term in the NEVER half is a second prohibition.
    `ALWAYS write `harmonic in $D$` — NEVER `harmonic on $D$``
    would otherwise read as mandating the form it bans.

    *One span per ALWAYS* — a sentence may carry several mandates, and a term in
    one of them is not licensed by another. Proof Style §5.2 runs "…Complex
    Analysis: ALWAYS $z$ and $z_0$ Real analysis or ODE: ALWAYS $x$ and $x_0$":
    "ODE" sits in the lead-in to the *second* mandate, and reading the sentence
    as one span made it look mandated by the first.
    """
    out: list[str] = []
    for hit in re.finditer(r"ALWAYS", sentence):
        span = sentence[hit.end():]
        stop = min((p for p in (span.find("ALWAYS"), span.find("NEVER")) if p >= 0),
                   default=-1)
        out.append(_strip_trailing_label(span if stop < 0 else span[:stop]))
    return out


def _strip_trailing_label(segment: str) -> str:
    """Drop a trailing `Label:` that introduces the *next* mandate.

    Splitting at ALWAYS is not enough on its own, because these sentences are
    written `Label: ALWAYS value  Label: ALWAYS value` — the label precedes its
    own keyword, so it lands at the end of the previous segment. That is the
    whole of both remaining false positives: "Image of the entire domain:"
    trailed Common §4.2's second mandate, and "Real analysis or ODE:" trailed
    Proof Style §5.2's.

    A label is bounded, and the bounds matter: it starts a clause, begins with a
    capital, carries no math, and is short. Without them the strip runs back to
    the start of the segment and deletes the mandate too — `$f(A)$ Image of the
    entire domain:` collapsed to the empty string, which suppresses the check
    rather than sharpening it.
    """
    return re.sub(r"(?<=\s)[A-Z][^.;:$]{0,60}:\s*$", "", segment)


def _demotion_reason(pair: parse.Pair,
                     allowlist: dict[tuple[str, str], str] | None = None,
                     sentences: list[tuple[str, str]] | None = None) -> str | None:
    """Why this pair must not be enforced, or None if it may be.

    Order matters. The conflicting-use check runs first and ignores the
    allowlist. Then an explicit entry, so a pair the owner has reasoned about
    carries that reasoning into the queue rather than a generic message. Then
    the qualifier rule, which the allowlist may override.
    """
    conflict = conflicting_use(pair, sentences or [])
    if conflict:
        where, sentence = conflict
        return (f"{pair.section} bans “{pair.banned}”, but {where} mandates it: "
                f"“{sentence[:200]}”. Enforcing the pair would rewrite text the "
                "documents require. A conflicting use is a fact about the "
                "documents, so no allowlist entry overrides it.")

    explicit = DEMOTED_PAIRS.get((pair.banned, pair.section))
    if explicit:
        return explicit

    # Failing closed on a qualifier applies to SUBSTITUTING rules only. It
    # exists because a wrong substitution corrupts the corpus and `relint`
    # applies it retroactively. A notation rule never rewrites anything — it
    # flags — so demoting one loses a check while preventing nothing.
    if pair.is_math:
        return None

    qualifier = qualifier_of(pair)
    if qualifier and (pair.banned, pair.section) not in (allowlist or {}):
        return (f"{pair.section} attaches a qualifier to the prohibition "
                f"(“{qualifier}”), so the ban is narrower than an "
                "unconditional substitution. The compiler represents "
                "unconditional pairs only and therefore fails closed. Add the "
                f"pair to rules/{ALLOWLIST_FILE} if the qualifier does not "
                "actually narrow the ban.")
    return None


def _frame_shaped(p: parse.Pair) -> bool:
    return not p.is_math and bool(FRAME_SHAPED.search(p.canonical + p.banned))


@dataclass
class Compiled:
    lexicon: dict
    symbols: dict
    validators: dict
    candidates: dict


def _yaml() -> YAML:
    y = YAML()
    y.default_flow_style = False
    y.width = 4096          # never wrap: a wrapped regex is a changed regex
    return y


def _dump(payload: dict) -> str:
    buf = io.StringIO()
    _yaml().dump(payload, buf)
    return HEADER + buf.getvalue()


def _label(name: str) -> str:
    return {"Common": "Common", "Proof_Style": "Proof Style"}.get(name, name)


def compile_field(field_key: str, rules_dir: Path) -> Compiled:
    allowlist = load_allowlist(rules_dir)
    sentences = _document_sentences(rules_dir, FIELD_DOCS.get(field_key))
    docs = []
    for rel in SHARED_DOCS:
        docs.append((parse.parse(rules_dir / rel), None))
    field_doc = FIELD_DOCS.get(field_key)
    if field_doc and (rules_dir / field_doc).exists():
        docs.append((parse.parse(rules_dir / field_doc), "field"))

    # Documents are visited lowest-precedence first, so a field ruling that
    # collides with a general one simply overwrites it (precedence header:
    # field file > Proof_Style > Common).
    prose: dict[str, parse.Pair] = {}
    notation: dict[str, parse.Pair] = {}
    all_pairs: list[parse.Pair] = []
    candidates: list[parse.Pair] = []

    for doc, role in docs:
        dest = DESTINATIONS[role or doc.name]
        if not dest:
            continue
        confident, proposed = parse.pairs(doc, _label(doc.name))
        confident = [p for p in confident if not _frame_shaped(p)]
        proposed = [p for p in proposed if not _frame_shaped(p)]
        all_pairs.extend(confident)
        candidates.extend(proposed)
        for p in confident:
            if p.is_math:
                if "symbols" in dest:
                    notation[p.banned] = p
            elif "lexicon" in dest or "validators" in dest:
                prose[p.banned] = p

    # A term mandated anywhere can never be banned anywhere. Common §16's
    # "NEVER use "positive" to mean $x >= 0$" is a semantic ruling wearing the
    # syntax of a terminology pair; this is what separates the two.
    canonical_terms = {p.canonical for p in all_pairs}
    # The containment guard consults proposed canonical terms too. A phrase the
    # documents mandate *somewhere* is part of the field's vocabulary even when
    # the sentence stating it was too loose to compile — and rewriting inside it
    # would be just as wrong. §13 states "linear fractional transformation" in
    # two sentences, so it is only a candidate, yet it is exactly what the
    # §5.5 `transformation -> mapping` substitution must not touch.
    vocabulary = canonical_terms | {p.canonical for p in candidates}
    demoted: list[parse.Pair] = []
    for table in (prose, notation):
        for banned, p in list(table.items()):
            if banned == p.canonical or banned in canonical_terms:
                del table[banned]
            elif _demotion_reason(p, allowlist, sentences):
                # A ban the document scopes in prose. Enforcing it unconditionally
                # would fire where the document says it must not.
                demoted.append(p)
                candidates.append(p)
                del table[banned]
            elif _contained_in_a_canonical(banned, vocabulary):
                # Not safely substitutable, so it becomes a proposal instead.
                # `transformation -> mapping` (§5.5) is a true ruling that would
                # nonetheless corrupt "linear fractional transformation", which
                # §13 mandates as a proper name; `entire -> an entire function`
                # (§5.1) would rewrite its own replacement. Both are real rules
                # about *bare* usage that a word-boundary rewrite cannot express.
                candidates.append(p)
                del table[banned]

    lexicon_pairs = {b: p for b, p in prose.items()
                     if p.document not in ("Common", "Proof_Style")}
    lexicon = _lexicon(lexicon_pairs, canonical_terms, all_pairs)
    symbols = _symbols(notation)
    validators = _validators(field_key, prose, notation, [d for d, _ in docs])
    return Compiled(lexicon=lexicon, symbols=symbols, validators=validators,
                    candidates=_candidates(candidates, canonical_terms, demoted,
                                           allowlist, sentences))


def _lexicon(prose: dict[str, parse.Pair], canonical_terms: set[str],
             all_pairs: list[parse.Pair]) -> dict:
    """`canonical:` plus a `banned:` substitution map (§I-5).

    Only pure-prose pairs land here, because substitution happens on prose runs
    with math excluded. A pair whose either side carries math cannot be applied
    by a word-boundary replacement and becomes a flag-only validator rule.
    """
    sections: dict[str, str] = {}
    for p in all_pairs:
        sections.setdefault(p.canonical, p.section)
    # The canonical list is the field's own vocabulary: a term this field
    # mandates in prose. It is what the new-term queue checks an unknown term
    # against, so a Common-owned word like "cannot" does not belong in it.
    terms = {p.canonical for p in prose.values()} | {
        p.canonical for p in all_pairs
        if p.document not in ("Common", "Proof_Style") and "$" not in p.canonical}
    canonical = [{"term": t, "section": sections[t]} for t in sorted(terms) if "$" not in t]
    banned = {b: p.canonical for b, p in sorted(prose.items())}
    return {"canonical": canonical, "banned": banned}


def _candidates(candidates: list[parse.Pair], canonical_terms: set[str],
                demoted: list[parse.Pair] | None = None,
                allowlist: dict[tuple[str, str], str] | None = None,
                sentences: list[tuple[str, str]] | None = None) -> dict:
    """Pairs the documents imply but do not state as an unconditional ruling.

    Not rulings. Each carries the sentence it came from so the owner can rule on
    it in one sitting (WP1.7) without going back to the document. Enforcing them
    unreviewed is what this file exists not to do.

    A `demoted` entry is different in kind from the rest: the document states it
    plainly, but *conditionally*, and the condition is prose no validator rule
    can carry. It is marked so the review sitting can tell "the parser was not
    sure" from "the parser was sure and the enforcement layer cannot express it".
    """
    reasons = {(p.canonical, p.banned): _demotion_reason(p, allowlist, sentences)
               for p in (demoted or [])}
    seen: dict[tuple[str, str], dict] = {}
    for p in candidates:
        if p.banned == p.canonical or p.banned in canonical_terms:
            continue
        key = (p.canonical, p.banned)
        entry = {
            "proposed_canonical": p.canonical,
            "proposed_banned": p.banned,
            "section": p.section,
            "is_math": p.is_math,
            "evidence": " ".join(p.evidence.split())[:300],
        }
        if reasons.get(key):
            entry["demoted"] = True
            entry["reason"] = " ".join(reasons[key].split())
        seen.setdefault(key, entry)
    return {"candidates": [seen[k] for k in sorted(seen)]}


def _symbols(notation: dict[str, parse.Pair]) -> dict:
    by_form: dict[str, dict] = {}
    for banned, p in sorted(notation.items()):
        key = p.canonical if p.target_certain else f"(see {p.section})"
        entry = by_form.setdefault(key, {"always": key, "never": [],
                                         "note": None, "section": p.section})
        if banned not in entry["never"]:
            entry["never"].append(banned)
    for e in by_form.values():
        e["never"].sort()
    return {"forms": [by_form[k] for k in sorted(by_form)]}


def _validators(field_key: str, prose: dict[str, parse.Pair],
                notation: dict[str, parse.Pair], docs) -> dict:
    rules: list[dict] = []

    for banned, p in sorted(prose.items()):
        rules.append({
            "id": _rule_id("sub", banned),
            "section": p.section,
            "kind": "substitute",
            "pattern": _word_pattern(banned),
            "message": f"{banned!r} is banned — always {p.canonical!r} ({p.section})",
            "fix": p.canonical,
            "scope": "prose",
            "except_phrases": [],
        })

    for banned, p in sorted(notation.items()):
        rules.append({
            "id": _rule_id("nota", banned),
            "section": p.section,
            "kind": "notation",
            # Flag only. A notation pair may sit inside math or straddle the
            # boundary, so an automatic replacement could corrupt an expression.
            "pattern": re.escape(banned),
            "message": (f"{banned} is banned — always {p.canonical} ({p.section})"
                        if p.target_certain
                        else f"{banned} is banned by {p.section}; see the rule "
                             "document for the mandated form"),
            "fix": None,
            "scope": "any",
            "except_phrases": [],
        })

    common = next(d for d in docs if d.name == "Common")
    rules += _forbidden(common)
    rules += _hyphenation(common)
    rules += _abbreviations(common)

    seen: dict[str, dict] = {}
    for r in rules:
        seen.setdefault(r["id"], r)
    return {"rules": [seen[k] for k in sorted(seen)]}


_FORBIDDEN_LINE = re.compile(r'^\s*[\"“]([^\"”]+)[\"”]\s*—\s*(?:forbidden|NEVER)')


_FIXED_PHRASES = re.compile(r"only in fixed phrases:(.*?)(?:\.\s|$)", re.S)


def _forbidden(common) -> list[dict]:
    """Common §14 — the words that are never used in any mathematical text.

    Two of the entries carry carve-outs in the same paragraph: "so" is permitted
    in "and so on", "do so", "if so", "even so". Those are extracted with the
    ban, because a rule that fires on "and so on" is a rule the owner turns off.
    """
    sec = common.section("14")
    if sec is None or sec.stub:
        return []
    text = " ".join(" ".join(sec.lines).split())
    out = []
    for line in sec.lines:
        hit = _FORBIDDEN_LINE.match(line)
        if not hit:
            continue
        word = hit.group(1)
        out.append({
            "id": _rule_id("forbid", word),
            "section": "Common §14",
            "kind": "forbidden",
            "pattern": _word_pattern(word),
            "message": f"{word!r} is forbidden in all mathematical text (Common §14)",
            "fix": None,
            "scope": "prose",
            "except_phrases": _fixed_phrases(text, word),
        })
    return out


def _fixed_phrases(section_text: str, word: str) -> list[str]:
    out: list[str] = []
    for block in _FIXED_PHRASES.findall(section_text):
        for phrase in parse.quoted(block):
            if re.search(_word_pattern(word), phrase, re.IGNORECASE):
                out.append(phrase)
    return sorted(set(out))


def _hyphenation(common) -> list[dict]:
    """Common §13 — compound adjectives that are always hyphenated."""
    sec = common.section("13")
    if sec is None or sec.stub:
        return []
    out = []
    for term in parse.comma_list(sec):
        if "-" not in term:
            continue
        unhyphenated = term.replace("-", "")
        out.append({
            "id": _rule_id("hyph", term),
            "section": "Common §13",
            "kind": "hyphenation",
            "pattern": _word_pattern(unhyphenated),
            "message": f"{unhyphenated!r} must be written {term!r} (Common §13)",
            "fix": term,
            "scope": "prose",
            "except_phrases": [],
        })
    return out


_ABBREV_LINE = re.compile(r"^\s{2,}(.+?)\s+—\s+NEVER\s+(.+?)\s*$")


def _abbreviations(common) -> list[dict]:
    """Common §17 — result names are written in full, never abbreviated."""
    sec = common.section("17")
    if sec is None or sec.stub:
        return []
    out = []
    for line in sec.lines:
        hit = _ABBREV_LINE.match(line)
        if not hit:
            continue
        full, abbrev = hit.group(1).strip(), hit.group(2).strip()
        out.append({
            "id": _rule_id("abbr", abbrev),
            "section": "Common §17",
            "kind": "substitute",
            "pattern": _word_pattern(abbrev),
            "message": f"{abbrev!r} must be written in full as {full!r} (Common §17)",
            "fix": full,
            "scope": "prose",
            "except_phrases": [],
        })
    return out


def _contained_in_a_canonical(banned: str, canonical_terms: set[str]) -> bool:
    """True when substituting `banned` would also rewrite a mandated term."""
    pattern = re.compile(_word_pattern(banned), re.IGNORECASE)
    return any(pattern.search(term) for term in canonical_terms if term != banned)


def _word_pattern(term: str) -> str:
    """Word-boundary match, case-insensitively applied by the engine.

    `\\b` is wrong at a non-word edge (`i.e.` ends in a dot), so the boundary is
    asserted only where the term actually starts or ends with a word character.
    """
    escaped = re.escape(term)
    left = r"\b" if term[:1].isalnum() or term[:1] == "_" else ""
    right = r"\b" if term[-1:].isalnum() or term[-1:] == "_" else ""
    return f"{left}{escaped}{right}"


def _rule_id(prefix: str, term: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", term.lower()).strip("-")[:48]
    return f"{prefix}-{slug}" if slug else f"{prefix}-x"


# ── driver ────────────────────────────────────────────────────────────

def outputs(field_key: str, root: Path) -> dict[str, Path]:
    gen = Path(root) / "generated"
    return {
        "lexicon": gen / "lexicon" / f"{field_key}.yaml",
        "symbols": gen / "symbols" / f"{field_key}.yaml",
        "validators": gen / "validators" / f"{field_key}.yaml",
        "candidates": gen / "lexicon" / f"{field_key}.candidates.yaml",
    }


def _queue_demoted(field_key: str, compiled: Compiled, root: Path) -> int:
    """Raise a demoted pair on the new-term queue so it reaches a human.

    Write mode only — `--check` must stay side-effect free, since the
    pre-commit hook runs it. Queue entries are content-addressed, so repeated
    `make rules` runs neither multiply the entry nor overwrite a worked one.
    """
    from knowledge_base.pipeline.queues import Queues

    queues = Queues(root)
    count = 0
    for entry in compiled.candidates["candidates"]:
        if not entry.get("demoted"):
            continue
        queues.add("new-term", {
            "field": field_key,
            "term": entry["proposed_banned"],
            "proposed_canonical": entry["proposed_canonical"],
            "section": entry["section"],
            "evidence": entry["evidence"],
            "why": entry["reason"],
        }, entry_id=f"demoted-{field_key}-{_rule_id('pair', entry['proposed_banned'])}")
        count += 1
    return count


def run(root: Path = ROOT, check: bool = False) -> int:
    settings = load(Path(root) / "config.yaml")
    rules_dir = Path(root) / "rules"
    stale: list[str] = []

    for field_key in settings.field_names():
        compiled = compile_field(field_key, rules_dir)
        for name, path in outputs(field_key, root).items():
            text = _dump(getattr(compiled, name))
            if check:
                if not path.exists() or path.read_text(encoding="utf-8") != text:
                    stale.append(str(path.relative_to(root)))
                continue
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text, encoding="utf-8", newline="")
        if not check:
            queued = _queue_demoted(field_key, compiled, root)
            log.info("%s: %d banned terms, %d notation forms, %d validator rules, "
                     "%d candidates for review, %d demoted awaiting a ruling",
                     field_key, len(compiled.lexicon["banned"]),
                     len(compiled.symbols["forms"]), len(compiled.validators["rules"]),
                     len(compiled.candidates["candidates"]), queued)

    if check and stale:
        print("generated/ is stale — run `make rules`:", file=sys.stderr)
        for s in stale:
            print(f"  {s}", file=sys.stderr)
        return 1
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--check", action="store_true",
                    help="fail if generated/ differs from what rules/ produces")
    ap.add_argument("--root", type=Path, default=ROOT)
    args = ap.parse_args(argv)
    return run(root=args.root, check=args.check)


if __name__ == "__main__":
    sys.exit(main())
