"""The inner contract (§I-7) — what the model returns, typed.

Parsing is deliberately strict and deliberately layered:

1. the CLI's JSON **envelope** is parsed for the final assistant text;
2. the **inner contract** is cut from that text between the first `{` and the
   last `}`, `json.loads`-ed, then validated by pydantic.

Strictness is the point. A prompt that silently lost a section, or a model that
drifted into prose, must fail the *call* — not produce plausible wrong output for
a whole batch that nothing downstream can detect. Failures retry with the
validator errors appended; after two retries the batch parks.

`tmp_id`s are the model's local handles. They are mapped to fresh ULIDs on
acceptance, never before: an id that reached the store and then failed
validation would leave a hole in a ULID sequence that is supposed to be dense
and creation-ordered.
"""

from __future__ import annotations

import json
import re
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

# §I-7 — the shared exclusion vocabulary. Both prompts render from
# `taxonomy.excluded`; this enum is the parse-side half of the same list.
ExclusionClass = Literal[
    "question", "problem", "solution", "worked-demonstration", "recall-repeat",
    "narrative", "non-content", "foreign-subject", "source-correction",
]


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ExtractedItem(_Strict):
    tmp_id: str
    type: str
    form: str | None = None
    slots: dict[str, Any]
    title: str | None = None
    topic: str | None = None
    terms: list[str] = Field(default_factory=list)
    figure_refs: list[str] = Field(default_factory=list)


class Fragment(_Strict):
    continues: str                    # the ULID of an open item
    payload: dict[str, Any]


class Duplicate(_Strict):
    tmp_id_or_new: str
    of: str


class Unclassified(_Strict):
    capture_id: str
    region: list[float] | None = None
    transcription: str
    note: str | None = None


class PendingRef(_Strict):
    tmp_id: str
    identifier: str                   # "Theorem 2.4", "(2)", "Sec. 1"


class FigureRegion(_Strict):
    parent: str                       # tmp-id or ULID
    capture_id: str
    bbox: list[float]


class Coverage(_Strict):
    capture_id: str
    region: list[float] | None = None
    disposition: str                  # items:<tmp-id[,…]> | excluded:<reason> | blank

    def kind(self) -> str:
        return self.disposition.split(":", 1)[0]

    def items(self) -> list[str]:
        if self.kind() != "items":
            return []
        return [t.strip() for t in self.disposition.split(":", 1)[1].split(",") if t.strip()]

    def reason(self) -> str | None:
        return self.disposition.split(":", 1)[1] if self.kind() == "excluded" else None


class Extraction(_Strict):
    batch_id: str
    items: list[ExtractedItem] = Field(default_factory=list)
    fragments: list[Fragment] = Field(default_factory=list)
    duplicates: list[Duplicate] = Field(default_factory=list)
    unclassified: list[Unclassified] = Field(default_factory=list)
    pending_refs: list[PendingRef] = Field(default_factory=list)
    figures: list[FigureRegion] = Field(default_factory=list)
    coverage: list[Coverage] = Field(default_factory=list)
    terms: list[str] = Field(default_factory=list)
    notes: str | None = None


class AuditGap(_Strict):
    capture_id: str
    region: list[float] | None = None
    description: str


class ExclusionViolation(_Strict):
    capture_id: str
    region: list[float] | None = None
    reason: str


class Audit(_Strict):
    gaps: list[AuditGap] = Field(default_factory=list)
    exclusion_violations: list[ExclusionViolation] = Field(default_factory=list)

    @property
    def passed(self) -> bool:
        """§I-9: both arrays empty means the batch passes."""
        return not self.gaps and not self.exclusion_violations


class ContractError(ValueError):
    """The response could not be read as the contract. Carries the text to
    append to the retry prompt — the model is told exactly what failed."""


def extract_json(text: str) -> dict:
    """First `{` to last `}`, per §I-7. Nothing cleverer.

    Models wrap JSON in prose or fences often enough that a strict
    whole-string parse would retry on well-formed output; anything looser than
    this would happily parse a JSON object the model mentioned in passing.
    """
    start, end = text.find("{"), text.rfind("}")
    if start < 0 or end <= start:
        raise ContractError("no JSON object found in the response")
    blob = text[start:end + 1]
    try:
        return json.loads(blob)
    except json.JSONDecodeError as e:
        raise ContractError(f"the response is not valid JSON: {e}") from e


def parse_extraction(text: str) -> Extraction:
    try:
        return Extraction.model_validate(extract_json(text))
    except ContractError:
        raise
    except Exception as e:                                   # noqa: BLE001
        raise ContractError(f"the JSON does not match the contract:\n{e}") from e


def parse_audit(text: str) -> Audit:
    try:
        return Audit.model_validate(extract_json(text))
    except ContractError:
        raise
    except Exception as e:                                   # noqa: BLE001
        raise ContractError(f"the JSON does not match the audit contract:\n{e}") from e


# ── the CLI envelope ──────────────────────────────────────────────────

RATE_LIMIT = re.compile(
    r"rate.?limit|usage limit|quota exceeded|too many requests|overloaded",
    re.IGNORECASE)


class RateLimited(RuntimeError):
    """A limit signature was seen. §I-7: requeue the batch and halt extraction
    for the run — hammering a limit turns a pause into a longer pause."""


def envelope_text(raw: str) -> str:
    """The final assistant text out of `claude -p --output-format json`.

    The envelope's shape is B2 — unverified against the live CLI. Every field
    read here is optional and falls back to the next candidate, so a renamed key
    degrades to "could not find the text" rather than to a silent empty string.
    """
    if RATE_LIMIT.search(raw):
        raise RateLimited(raw.strip()[:400])
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        return raw          # a bare, non-JSON response is still worth parsing

    if isinstance(payload, dict):
        for key in ("result", "text", "content", "completion", "response"):
            value = payload.get(key)
            if isinstance(value, str) and value.strip():
                return value
            if isinstance(value, list):
                joined = "".join(
                    part.get("text", "") for part in value if isinstance(part, dict))
                if joined.strip():
                    return joined
        if payload.get("is_error") or payload.get("error"):
            message = str(payload.get("error") or payload.get("result") or "")
            if RATE_LIMIT.search(message):
                raise RateLimited(message[:400])
            raise ContractError(f"the CLI reported an error: {message[:400]}")
        # `--bare` may hand back the contract itself with no envelope around it.
        if {"batch_id", "items", "gaps", "exclusion_violations"} & set(payload):
            return raw
    raise ContractError(
        "no assistant text in the CLI envelope — the envelope shape has changed "
        "(B2); inspect state/calls/ for the recorded response")
