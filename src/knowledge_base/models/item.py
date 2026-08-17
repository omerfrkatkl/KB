"""The item — the unit the whole system stores, merges, and renders (§I-3).

`provenance` is append-only and is the only path back from a rendered sentence to
the pixels it came from. Nothing in this module ever removes an entry from it.

`kind` and `capture` are independent axes (A23/A24): `kind` is semantic and comes
from the folder, `capture` is geometric and comes from the file. `kind` decides
the exam star, so it is never inferred from the image.
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator
from ulid import ULID

from knowledge_base.models.slots import SLOTS_BY_TYPE

SCHEMA_VERSION = 1


class ItemType(StrEnum):
    DEFINITION = "definition"
    THEOREM = "theorem"
    LEMMA = "lemma"
    PROPOSITION = "proposition"
    COROLLARY = "corollary"
    CLAIM = "claim"
    COUNTEREXAMPLE = "counterexample"
    AXIOM = "axiom"
    NOTATION = "notation"
    REMARK = "remark"


class Status(StrEnum):
    OPEN = "open"            # started but unfinished structure
    ACTIVE = "active"        # complete; builds
    FLAGGED = "flagged"      # in a queue; excluded from builds
    SUPERSEDED = "superseded"  # terminal; kept for provenance, never built


class Kind(StrEnum):
    BOARD = "board"
    TEXTBOOK = "textbook"


class Capture(StrEnum):
    PDF = "pdf"
    PHOTO = "photo"
    RASTER = "raster"


class _Model(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Extractor(_Model):
    """Which prompt and model produced this item (§I-1). Never re-derived."""
    cli_version: str | None = None
    model: str | None = None
    prompt_hash: str | None = None
    dialect: str | None = None


class Provenance(_Model):
    source: str | None = None          # null until an unsorted drop is answered (A25)
    kind: Kind
    capture: Capture
    page: int | None = None            # pdf only
    locator: str | None = None         # "§54", "Theorem 2.4" — raster/board
    region: list[float] | None = None  # [x, y, w, h] in capture coordinates
    image_sha256: str | None = None
    group: str | None = None           # capture group (§I-6.5)
    photo: str | None = None           # originating photo path, board x photo
    capture_id: str | None = None      # which staged image in the batch
    extractor: Extractor | None = None


class FigureOrigin(_Model):
    provenance_index: int
    bbox: list[float]


class Figure(_Model):
    asset: str
    caption: str | None = None
    origin: FigureOrigin


class Item(_Model):
    id: str
    schema_version: int = SCHEMA_VERSION
    field: str
    type: ItemType
    slots: dict[str, Any]
    title: str | None = None
    terms_used: list[str] = Field(default_factory=list)
    topic: str | None = None
    order: int | None = None
    exam_star: Literal["auto"] | bool = "auto"
    status: Status = Status.ACTIVE
    superseded_by: str | None = None
    refs: list[str] = Field(default_factory=list)
    provenance: list[Provenance] = Field(default_factory=list)
    figures: list[Figure] = Field(default_factory=list)
    created: datetime
    updated: datetime

    @model_validator(mode="after")
    def _slots_match_type(self):
        model = SLOTS_BY_TYPE[self.type.value]
        # Validate, then keep the *validated* dict so defaults are materialised
        # once and every downstream reader sees the same keys.
        object.__setattr__(self, "slots", model.model_validate(self.slots).model_dump())
        return self

    # ── derived properties ────────────────────────────────────────────
    @property
    def starred(self) -> bool:
        """A6: derived from board provenance, overridable by `kb star`."""
        if isinstance(self.exam_star, bool):
            return self.exam_star
        return any(p.kind is Kind.BOARD for p in self.provenance)

    @property
    def builds(self) -> bool:
        return self.status in (Status.ACTIVE, Status.OPEN) and self.status is not Status.FLAGGED

    def typed_slots(self):
        return SLOTS_BY_TYPE[self.type.value].model_validate(self.slots)


def now() -> datetime:
    return datetime.now(timezone.utc).replace(microsecond=0)


def new_id() -> str:
    return str(ULID())


def make(
    *,
    field: str,
    type: str | ItemType,
    slots: dict[str, Any],
    id: str | None = None,
    **kw: Any,
) -> Item:
    ts = now()
    return Item(
        id=id or new_id(),
        field=field,
        type=ItemType(type),
        slots=slots,
        created=kw.pop("created", ts),
        updated=kw.pop("updated", ts),
        **kw,
    )
