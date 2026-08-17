"""Validation (§I-8) — ordered, and each failure names its route.

The order is not cosmetic. Cheap structural checks run before expensive semantic
ones, and every check states where a failure goes: back to the extractor as a
retry, into a queue for a ruling, or onto the item as a status change. A check
that merely returns "invalid" would leave the caller to invent a policy.

Two things this stage does **not** do:

* It never rewrites a slot to make it fit. The one exception is a lexicon
  substitution, which is a *pure pair* stated by the owner in a rule document —
  deterministic, logged, and reversible by editing the document.
* It never marks an item `open` for having no proof. Sources legitimately state
  results without argument (§I-3); `open` means a *started but unfinished*
  structure — a proof missing its conclusion, a declared-but-absent case.

The rule engine (step 4A) is where the regex layer earns its keep. Frames own
generated prose, so a regex over rendered output is only a regression test. The
engine's live job is the text an LLM actually produced: slot content, checked
before storage.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any, Iterable

from knowledge_base.models.item import Item, Status
from knowledge_base.models.profile import Profile, ValidatorRule
from knowledge_base.models.slots import SLOTS_BY_TYPE
from knowledge_base.ops.log import get

log = get("validate")

REF_TOKEN = re.compile(r"\{ref:([0-9A-HJKMNP-TV-Z]{26})\}")
REF_TOKEN_LOOSE = re.compile(r"\{ref:([^}]*)\}")
MATH_RUN = re.compile(r"\$[^$]*\$")


class Route(StrEnum):
    """Where a failure goes. Every finding carries one."""
    RETRY = "retry"                  # back to the extractor with the error text
    UNCLASSIFIED = "unclassified"    # to the unclassified queue
    NEW_TERM = "new-term"
    PENDING_REF = "pending-ref"
    FLAG = "flag"                    # item -> flagged, awaiting a ruling
    OPEN = "open"                    # item -> open, awaiting continuation
    FIXED = "fixed"                  # deterministic substitution, applied + logged


@dataclass
class Finding:
    check: str
    route: Route
    message: str
    slot: str | None = None
    detail: dict[str, Any] = field(default_factory=dict)


@dataclass
class Result:
    item: Item
    findings: list[Finding] = field(default_factory=list)
    substitutions: list[tuple[str, str, str]] = field(default_factory=list)
    unknown_terms: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not any(f.route in (Route.RETRY, Route.UNCLASSIFIED) for f in self.findings)

    def routed(self, route: Route) -> list[Finding]:
        return [f for f in self.findings if f.route is route]

    def status(self) -> Status:
        if self.routed(Route.FLAG) or self.routed(Route.PENDING_REF):
            return Status.FLAGGED
        if self.routed(Route.OPEN):
            return Status.OPEN
        return Status.ACTIVE


# ── 2. Slot Text Grammar ──────────────────────────────────────────────

def prose_runs(text: str) -> list[str]:
    """Everything outside `$…$`. Substitution and word rules apply here only."""
    return MATH_RUN.split(text)


def check_stg(text: str, slot: str, known_ids: set[str] | None = None) -> list[Finding]:
    out: list[Finding] = []
    if text.count("$") % 2:
        out.append(Finding("stg.balanced-math", Route.RETRY,
                           f"{slot}: unbalanced `$` — every inline math run must close",
                           slot=slot))
    for raw in REF_TOKEN_LOOSE.findall(text):
        if not REF_TOKEN.fullmatch("{ref:%s}" % raw):
            out.append(Finding("stg.ref-token", Route.RETRY,
                               f"{slot}: {{ref:{raw}}} is not a ULID", slot=slot))
    if "\n" in text:
        out.append(Finding("stg.no-line-breaks", Route.RETRY,
                           f"{slot}: line breaks are not part of the slot grammar; "
                           "structure belongs to frames", slot=slot))
    for marker in ("**", "##", "- ", "* "):
        if text.startswith(marker):
            out.append(Finding("stg.no-markup", Route.RETRY,
                               f"{slot}: markup is not permitted in slot text", slot=slot))
            break
    return out


def slot_texts(item: Item) -> list[tuple[str, str]]:
    """(slot path, text) for every prose-carrying slot, proofs included."""
    out: list[tuple[str, str]] = []

    def walk(node: Any, path: str) -> None:
        if isinstance(node, str):
            out.append((path, node))
        elif isinstance(node, dict):
            for k, v in node.items():
                if k in ("kind", "method", "form", "article", "establishes",
                         "setup_form", "transition", "ref", "target"):
                    continue
                walk(v, f"{path}.{k}" if path else k)
        elif isinstance(node, list):
            for i, v in enumerate(node):
                walk(v, f"{path}[{i}]")

    walk(item.slots, "")
    return out


# ── 4/4A. lexicon and the rule engine ─────────────────────────────────

def apply_lexicon(text: str, banned: dict[str, str]) -> tuple[str, list[tuple[str, str]]]:
    """Longest-match, word-boundary, case-preserving-first-letter substitution.

    Applied to prose runs only: a term inside `$…$` is notation, and rewriting it
    would corrupt an expression.
    """
    applied: list[tuple[str, str]] = []
    parts = MATH_RUN.split(text)
    maths = MATH_RUN.findall(text)
    for i, part in enumerate(parts):
        for variant in sorted(banned, key=len, reverse=True):
            pattern = re.compile(_boundary(variant), re.IGNORECASE)
            if pattern.search(part):
                part = pattern.sub(lambda m, c=banned[variant]: _match_case(m.group(0), c), part)
                applied.append((variant, banned[variant]))
        parts[i] = part
    rebuilt = "".join(p + (maths[i] if i < len(maths) else "") for i, p in enumerate(parts))
    return rebuilt, applied


def _boundary(term: str) -> str:
    escaped = re.escape(term)
    left = r"\b" if term[:1].isalnum() else ""
    right = r"\b" if term[-1:].isalnum() else ""
    return f"{left}{escaped}{right}"


def _match_case(matched: str, canonical: str) -> str:
    if matched[:1].isupper() and canonical[:1].islower():
        return canonical[0].upper() + canonical[1:]
    return canonical


def run_rules(text: str, rules: Iterable[ValidatorRule]) -> tuple[str, list[Finding], list]:
    """Step 4A. Pure pairs are substituted; everything else is flagged."""
    findings: list[Finding] = []
    applied: list[tuple[str, str, str]] = []
    for rule in rules:
        pattern = re.compile(rule.pattern, re.IGNORECASE)
        targets = prose_runs(text) if rule.scope == "prose" else [text]
        hits = [m.group(0) for t in targets for m in pattern.finditer(t)]
        hits = [h for h in hits if not _excused(text, h, rule)]
        if not hits:
            continue
        if rule.fix:
            new = _substitute(text, pattern, rule)
            applied.append((rule.id, hits[0], rule.fix))
            text = new
            findings.append(Finding(f"rules.{rule.id}", Route.FIXED, rule.message))
        else:
            findings.append(Finding(f"rules.{rule.id}", Route.FLAG, rule.message,
                                    detail={"matched": hits[0]}))
    return text, findings, applied


def _excused(text: str, hit: str, rule: ValidatorRule) -> bool:
    """A match inside one of the rule's fixed phrases is not a violation."""
    low = text.lower()
    return any(phrase.lower() in low and hit.lower() in phrase.lower()
               for phrase in rule.except_phrases)


def _substitute(text: str, pattern: re.Pattern, rule: ValidatorRule) -> str:
    if rule.scope != "prose":
        return pattern.sub(rule.fix, text)
    parts, maths = MATH_RUN.split(text), MATH_RUN.findall(text)
    parts = [pattern.sub(lambda m: _match_case(m.group(0), rule.fix), p) for p in parts]
    return "".join(p + (maths[i] if i < len(maths) else "") for i, p in enumerate(parts))


# ── 6. completeness ───────────────────────────────────────────────────

def check_completeness(item: Item) -> list[Finding]:
    """Incomplete structure -> `open`. An empty `proofs[]` is NOT incompleteness."""
    out: list[Finding] = []
    for path, proof in _proofs(item):
        if not proof.get("conclusion"):
            out.append(Finding("complete.proof-conclusion", Route.OPEN,
                               f"{path}: proof has no conclusion — the argument stops "
                               "mid-way and is awaiting continuation", slot=path))
        for block in ("base", "inductive", "existence", "uniqueness",
                      "forward", "backward", "subset", "superset"):
            b = proof.get(block)
            if isinstance(b, dict) and not b.get("steps") and not b.get("conclusion"):
                out.append(Finding("complete.empty-block", Route.OPEN,
                                   f"{path}.{block}: declared but empty", slot=path))
        for i, case in enumerate(proof.get("cases") or []):
            if not case.get("steps"):
                out.append(Finding("complete.empty-case", Route.OPEN,
                                   f"{path}.cases[{i}]: declared but has no steps",
                                   slot=path))
    return out


def _proofs(item: Item) -> list[tuple[str, dict]]:
    return [(f"proofs[{i}]", p) for i, p in enumerate(item.slots.get("proofs") or [])]


# ── 8. reference integrity ────────────────────────────────────────────

def check_refs(item: Item, known_ids: set[str]) -> list[Finding]:
    """An unresolved ref must never be rendered as vague prose (§I-8.8)."""
    out: list[Finding] = []
    for slot, text in slot_texts(item):
        for ulid in REF_TOKEN.findall(text):
            if ulid not in known_ids:
                out.append(Finding("refs.unresolved", Route.PENDING_REF,
                                   f"{slot}: {{ref:{ulid}}} resolves to nothing in the store",
                                   slot=slot, detail={"ref": ulid}))
    for path, proof in _proofs(item):
        for i, step in enumerate(proof.get("steps") or []):
            ref = (step.get("justification") or {}).get("ref")
            if ref and ref not in known_ids:
                out.append(Finding("refs.unresolved", Route.PENDING_REF,
                                   f"{path}.steps[{i}]: justification cites {ref}, "
                                   "which is not in the store",
                                   slot=path, detail={"ref": ref}))
    return out


# ── the ordered pass ──────────────────────────────────────────────────

def validate(item: Item, profile: Profile, known_ids: set[str] | None = None) -> Result:
    """Run §I-8 steps 1–8 in order. Step 9 (compile smoke) is `build.compile`."""
    known = known_ids or set()
    result = Result(item=item)
    slots = dict(item.slots)

    # 1. inner-contract shape — pydantic, already applied on construction, but
    #    re-asserted here because an item may arrive from a hand edit.
    try:
        SLOTS_BY_TYPE[item.type.value].model_validate(slots)
    except Exception as e:                                  # noqa: BLE001
        result.findings.append(Finding("schema.slots", Route.RETRY, str(e)))
        return result

    # 3. type must be in the taxonomy — the taxonomy IS the allowlist.
    if not profile.taxonomy.allows(item.type.value):
        result.findings.append(Finding(
            "taxonomy.excluded", Route.UNCLASSIFIED,
            f"{item.type.value} is not in this field's taxonomy"))
        return result

    # 2. STG, 4. lexicon, 4A. rule engine — per prose slot.
    changed: dict[str, str] = {}
    for slot, text in slot_texts(item):
        result.findings += check_stg(text, slot, known)
        new, applied = apply_lexicon(text, profile.lexicon.banned)
        for variant, canonical in applied:
            result.substitutions.append((slot, variant, canonical))
            result.findings.append(Finding(
                "lexicon.substituted", Route.FIXED,
                f"{slot}: {variant!r} -> {canonical!r}", slot=slot))
        new, rule_findings, rule_applied = run_rules(new, profile.validators.rules)
        for rid, hit, fix in rule_applied:
            result.substitutions.append((slot, hit, fix))
        result.findings += [f if f.slot else Finding(f.check, f.route, f.message, slot,
                                                     f.detail) for f in rule_findings]
        if new != text:
            changed[slot] = new

    if changed:
        item = item.model_copy(update={"slots": _apply(item.slots, changed)})
        result.item = item

    # 4. unknown terms -> new-term queue. Load-bearing ones also flag the item.
    result.unknown_terms = unknown_terms(item, profile)
    for term in result.unknown_terms:
        load_bearing = _in_statement_slot(item, term)
        result.findings.append(Finding(
            "lexicon.unknown-term", Route.FLAG if load_bearing else Route.NEW_TERM,
            f"unknown technical term {term!r}"
            + (" in a statement slot" if load_bearing else ""),
            detail={"term": term, "load_bearing": load_bearing}))

    # 6. completeness, 8. ref integrity
    result.findings += check_completeness(item)
    result.findings += check_refs(item, known)
    return result


def _apply(slots: dict, changed: dict[str, str]) -> dict:
    import copy

    out = copy.deepcopy(slots)
    for path, value in changed.items():
        node, key = _resolve(out, path)
        node[key] = value
    return out


def _resolve(root: Any, path: str):
    parts = re.findall(r"([A-Za-z_]+)|\[(\d+)\]", path)
    node = root
    trail = [(name or int(index)) for name, index in parts]
    for step in trail[:-1]:
        node = node[step]
    return node, trail[-1]


def unknown_terms(item: Item, profile: Profile) -> list[str]:
    """Terms the extractor reported that the lexicon does not know."""
    known = {t.lower() for t in profile.lexicon.canonical_terms()}
    known |= {b.lower() for b in profile.lexicon.banned}
    return sorted({t for t in item.terms_used if t.lower() not in known})


STATEMENT_SLOTS = ("term", "body", "conclusion", "hypotheses", "citation_form",
                   "witness", "witness_properties")


def _in_statement_slot(item: Item, term: str) -> bool:
    pattern = re.compile(_boundary(term), re.IGNORECASE)
    return any(pattern.search(text) for slot, text in slot_texts(item)
               if slot.split(".")[0].split("[")[0] in STATEMENT_SLOTS)
