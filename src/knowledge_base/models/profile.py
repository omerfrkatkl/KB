"""Per-field profile files (§I-5): taxonomy, lexicon, symbols, outline, sources.

The taxonomy file *is* the emitter allowlist. Its `excluded:` block is embedded
verbatim in both prompts, so the extractor and the auditor are reading one
written policy rather than two copies that drift.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator
from ruamel.yaml import YAML

from knowledge_base.config import ROOT


class _Model(BaseModel):
    model_config = ConfigDict(extra="forbid")


class TaxonomyEntry(_Model):
    key: str
    render: str            # template function, e.g. "thm"
    numbered: bool
    schema_name: str = Field(alias="schema")
    note: str              # the one-line description both prompts show

    model_config = ConfigDict(extra="forbid", populate_by_name=True)


class ExcludedClass(_Model):
    key: str
    definition: str


class Taxonomy(_Model):
    types: list[TaxonomyEntry]
    excluded: list[ExcludedClass]

    def keys(self) -> list[str]:
        return [t.key for t in self.types]

    def entry(self, key: str) -> TaxonomyEntry:
        for t in self.types:
            if t.key == key:
                return t
        raise KeyError(f"{key} is not in the taxonomy — the taxonomy is the emitter allowlist")

    def allows(self, key: str) -> bool:
        return any(t.key == key for t in self.types)


class Lexicon(_Model):
    canonical: list[dict[str, Any]] = Field(default_factory=list)
    banned: dict[str, str] = Field(default_factory=dict)

    def canonical_terms(self) -> set[str]:
        return {c["term"] for c in self.canonical}


class NotationForm(_Model):
    """A compiled notation ruling from `rules/` — the mandated form and the
    forms it displaces. Feeds the symbol lint and the prompt's notation block."""
    always: str
    never: list[str] = Field(default_factory=list)
    note: str | None = None
    section: str


class Symbols(_Model):
    forms: list[NotationForm] = Field(default_factory=list)


class Binding(_Model):
    """A `#let` emitted into `build/<field>/symbols-gen.typ`. Authored in the
    field profile, not compiled: the rule documents mandate notation *forms*,
    and which of them deserve a shorthand is a typesetting decision."""
    name: str
    value: str
    note: str | None = None


class Bindings(_Model):
    bindings: list[Binding] = Field(default_factory=list)


class Chapter(_Model):
    key: str
    title: str
    topics: list[str] = Field(default_factory=list)


class Outline(_Model):
    chapters: list[Chapter] = Field(default_factory=list)

    def topic_order(self) -> dict[str, tuple[int, int]]:
        """topic -> (chapter index, position within chapter)."""
        out: dict[str, tuple[int, int]] = {}
        for ci, ch in enumerate(self.chapters):
            for ti, topic in enumerate(ch.topics):
                out[topic] = (ci, ti)
        return out


class Source(_Model):
    key: str
    kind: str              # textbook | board — same two values as provenance.kind
    title: str
    citation: str | None = None
    rank: int = 100
    conventions: str | None = None

    @model_validator(mode="after")
    def _kind_is_shared_vocabulary(self):
        if self.kind not in ("textbook", "board"):
            raise ValueError("source kind must be `textbook` or `board` — no third spelling")
        return self


class Sources(_Model):
    sources: list[Source] = Field(default_factory=list)

    def get(self, key: str) -> Source | None:
        return next((s for s in self.sources if s.key == key), None)

    def rank(self, key: str | None) -> int:
        s = self.get(key) if key else None
        return s.rank if s else 10_000  # unknown sources sort last, never first


class ValidatorRule(_Model):
    """One compiled check on transcribed slot content (§I-8 step 4A)."""
    id: str
    section: str
    kind: Literal["substitute", "forbidden", "hyphenation", "notation"]
    pattern: str
    message: str
    fix: str | None = None          # set iff the rule is a pure pair
    scope: Literal["prose", "math", "any"] = "prose"
    except_phrases: list[str] = Field(default_factory=list)


class Validators(_Model):
    rules: list[ValidatorRule] = Field(default_factory=list)


class Profile(_Model):
    field: str
    taxonomy: Taxonomy
    lexicon: Lexicon
    symbols: Symbols
    validators: Validators
    bindings: Bindings
    outline: Outline
    sources: Sources


def _yaml() -> YAML:
    y = YAML()
    y.preserve_quotes = True
    return y


def _plain(obj):
    if hasattr(obj, "items"):
        return {str(k): _plain(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_plain(v) for v in obj]
    return obj


def _read(path: Path, model: type[_Model], default: dict | None = None):
    if not path.exists():
        if default is None:
            raise FileNotFoundError(f"profile file missing: {path}")
        return model.model_validate(default)
    return model.model_validate(_plain(_yaml().load(path.read_text(encoding="utf-8"))) or default or {})


def profile_dir(field: str, root: Path = ROOT) -> Path:
    return root / "fields" / field / "profile"


def load_profile(field: str, root: Path = ROOT) -> Profile:
    """Load a field's profile.

    The lexicon and symbols come from `generated/` (compiled from `rules/`,
    WP1.4A) when present, and fall back to empty. Empty is a legitimate state —
    Phase 1 runs with an empty lexicon by design — but it is never *silently*
    empty: `knowledge-base status` reports it.
    """
    d = profile_dir(field, root)
    gen = root / "generated"
    return Profile(
        field=field,
        taxonomy=_read(d / "taxonomy.yaml", Taxonomy),
        lexicon=_read(gen / "lexicon" / f"{field}.yaml", Lexicon, default={}),
        symbols=_read(gen / "symbols" / f"{field}.yaml", Symbols, default={}),
        validators=_read(gen / "validators" / f"{field}.yaml", Validators, default={}),
        bindings=_read(d / "symbols.yaml", Bindings, default={}),
        outline=_read(d / "outline.yaml", Outline, default={}),
        sources=_read(d / "sources.yaml", Sources, default={}),
    )
