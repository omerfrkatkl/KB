"""Per-type slot models and the proof grammar (plan §I-3).

Two rules govern every model here and neither is negotiable:

* **Extend, never change** (A7). A new shape gets a new optional field or a new
  variant. Repurposing an existing field silently rewrites the meaning of every
  item already stored under the old reading.
* **No free-prose escape hatch.** There is no `notes` slot, no `other` variant.
  Material that does not fit goes to a review queue; a forced fit is invisible
  downstream, which is the one error regeneration cannot repair.

Slot prose is in Slot Text Grammar (STG): plain Unicode, inline math `$…$`,
reference tokens `{ref:<ulid>}`, nothing else. The grammar is *checked* in
`pipeline/validate.py`, not here — pydantic validates shape, the validator
validates content, and keeping them apart means a schema change never silently
loosens a content rule.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class _Slots(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ProofMethod(StrEnum):
    DIRECT = "direct"
    CONTRADICTION = "contradiction"
    CONTRAPOSITIVE = "contrapositive"
    INDUCTION = "induction"
    STRONG_INDUCTION = "strong-induction"
    CONSTRUCTION = "construction"
    CASES = "cases"
    UNIQUENESS_PAIR = "uniqueness-pair"
    IFF_PAIR = "iff-pair"
    DOUBLE_INCLUSION = "double-inclusion"
    VERIFY_CRITERIA = "verify-criteria"
    COMPUTATION = "computation"


class JustificationKind(StrEnum):
    BY_HYPOTHESIS = "by-hypothesis"
    BY_INDUCTIVE_HYPOTHESIS = "by-inductive-hypothesis"
    BY_DEFINITION = "by-definition"
    BY_REF = "by-ref"
    BY_FACT = "by-fact"
    BY_COMPUTATION = "by-computation"
    BY_MECHANICAL = "by-mechanical"
    BY_PREVIOUS_STEP = "by-previous-step"


# Proof Style §3.2 — the only transitions an extractor may name explicitly. The
# other three ("Therefore", "Then", "This gives") are *derived* from the
# justification kind by frames.py and must never be supplied as data.
Transition = Literal["Note that", "Similarly", "Moreover"]


class Justification(_Slots):
    kind: JustificationKind
    term: str | None = None      # iff by-definition
    ref: str | None = None       # iff by-ref; optional on by-fact/by-definition (A20)
    fact: str | None = None      # iff by-fact
    content: str | None = None   # iff by-previous-step
    transition: Transition | None = None

    @model_validator(mode="after")
    def _fields_match_kind(self):
        k = self.kind
        required = {
            JustificationKind.BY_DEFINITION: "term",
            JustificationKind.BY_REF: "ref",
            JustificationKind.BY_FACT: "fact",
            JustificationKind.BY_PREVIOUS_STEP: "content",
        }.get(k)
        if required and getattr(self, required) is None:
            raise ValueError(f"justification kind {k} requires `{required}`")
        # `ref` is permitted on by-fact and by-definition — that optional pairing
        # is exactly what makes A20's build-time membership check possible.
        allowed_ref = {
            JustificationKind.BY_REF,
            JustificationKind.BY_FACT,
            JustificationKind.BY_DEFINITION,
        }
        if self.ref is not None and k not in allowed_ref:
            raise ValueError(f"justification kind {k} may not carry `ref`")
        for name in ("term", "fact", "content"):
            owner = {"term": JustificationKind.BY_DEFINITION,
                     "fact": JustificationKind.BY_FACT,
                     "content": JustificationKind.BY_PREVIOUS_STEP}[name]
            if getattr(self, name) is not None and k is not owner:
                raise ValueError(f"justification kind {k} may not carry `{name}`")
        return self


class Step(_Slots):
    claim: str
    justification: Justification


class StepBlock(_Slots):
    """A named run of steps with its own conclusion — a case, a direction, a half."""
    steps: list[Step] = Field(default_factory=list)
    conclusion: str | None = None


class Case(StepBlock):
    condition: str


class InductiveBlock(StepBlock):
    hypothesis: str


class Criterion(StepBlock):
    name: str


class Proof(_Slots):
    method: ProofMethod
    setup: str | None = None
    setup_form: Literal["assume", "sufficiency"] = "assume"
    steps: list[Step] = Field(default_factory=list)
    conclusion: str | None = None
    contradicts: str | None = None                      # contradiction (§4.2)

    base: StepBlock | None = None                       # induction (§4.4)
    inductive: InductiveBlock | None = None
    cases: list[Case] = Field(default_factory=list)     # cases (§4.3)
    existence: StepBlock | None = None                  # uniqueness-pair (§4.7)
    uniqueness: StepBlock | None = None
    forward: StepBlock | None = None                    # iff-pair (§4.5)
    backward: StepBlock | None = None
    subset: StepBlock | None = None                     # double-inclusion
    superset: StepBlock | None = None
    definition: str | None = None                       # verify-criteria
    criteria: list[Criterion] = Field(default_factory=list)

    @model_validator(mode="after")
    def _substructure_matches_method(self):
        m = self.method
        need: dict[ProofMethod, tuple[str, ...]] = {
            ProofMethod.INDUCTION: ("base", "inductive"),
            ProofMethod.STRONG_INDUCTION: ("base", "inductive"),
            ProofMethod.CASES: ("cases",),
            ProofMethod.UNIQUENESS_PAIR: ("existence", "uniqueness"),
            ProofMethod.IFF_PAIR: ("forward", "backward"),
            ProofMethod.DOUBLE_INCLUSION: ("subset", "superset"),
            ProofMethod.VERIFY_CRITERIA: ("definition", "criteria"),
            ProofMethod.CONTRADICTION: ("contradicts",),
        }.get(m, ())
        for f in need:
            v = getattr(self, f)
            if v is None or (isinstance(v, list) and not v):
                raise ValueError(f"proof method {m} requires `{f}`")
        if m is ProofMethod.CASES and len(self.cases) < 2:
            raise ValueError("proof by cases requires at least two cases (§4.3)")
        return self


# ── per-type slot models (§I-3) ───────────────────────────────────────────

class DefinitionSlots(_Slots):
    term: str
    form: Literal["noun", "predicate"] = "noun"
    article: Literal["a", "an", "the", "none"] = "a"
    subject: str | None = None    # predicate form: the object being qualified
    scope: str | None = None      # predicate form: "in $D$", "on $[a,b]$"
    context: str | None = None    # ambient assumptions -> "Let [context]. "
    body: str

    @model_validator(mode="after")
    def _form_requirements(self):
        if self.form == "predicate" and not self.subject:
            raise ValueError("predicate-form definitions require `subject` (Common §21.1)")
        return self


class ResultSlots(_Slots):
    """theorem | lemma | proposition | corollary."""
    name: str | None = None
    citation_form: str                                  # REQUIRED (A21, Common §21.3)
    hypotheses: list[str] = Field(default_factory=list)
    conclusion: str
    proofs: list[Proof] = Field(default_factory=list)   # may be legitimately empty
    converse_holds: bool | None = None


class ClaimSlots(_Slots):
    body: str
    citation_form: str                                  # REQUIRED (A21)
    proofs: list[Proof] = Field(default_factory=list)


class CounterexampleSlots(_Slots):
    """A12 + Common §21.4 — admitted only for (a) converse-false or (b) necessity."""
    target: str                                         # ulid of the result
    establishes: Literal["converse-false", "hypothesis-necessary"]
    hypothesis: str | None = None                       # required iff necessity
    witness: str
    witness_properties: str

    @model_validator(mode="after")
    def _necessity_names_its_hypothesis(self):
        if self.establishes == "hypothesis-necessary" and not self.hypothesis:
            raise ValueError("hypothesis-necessary counterexamples must name the hypothesis")
        if self.establishes == "converse-false" and self.hypothesis:
            raise ValueError("converse-false counterexamples carry no `hypothesis`")
        return self


class ProseSlots(_Slots):
    """axiom | notation | remark — one fact per item (extraction rule)."""
    body: str


SLOTS_BY_TYPE: dict[str, type[_Slots]] = {
    "definition": DefinitionSlots,
    "theorem": ResultSlots,
    "lemma": ResultSlots,
    "proposition": ResultSlots,
    "corollary": ResultSlots,
    "claim": ClaimSlots,
    "counterexample": CounterexampleSlots,
    "axiom": ProseSlots,
    "notation": ProseSlots,
    "remark": ProseSlots,
}
