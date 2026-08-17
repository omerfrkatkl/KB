"""JSON Schemas for the prompts, generated from the pydantic models (§I-1).

Single source of truth: the extractor is told the same shape the validator will
enforce. A hand-maintained second copy would drift, and the drift would show up
as a retry loop on well-formed output.

`for_types` narrows the pack to the types a phase actually accepts — WP1.3 wants
Phase-1 types only, and the plan is explicit that this is done "by config rather
than by editing the templates".
"""

from __future__ import annotations

import json
from typing import Any, Iterable

from knowledge_base.models.slots import SLOTS_BY_TYPE


def slot_schema(type_key: str) -> dict[str, Any]:
    schema = SLOTS_BY_TYPE[type_key].model_json_schema(mode="validation")
    schema["title"] = f"{type_key} slots"
    return schema


def for_types(types: Iterable[str]) -> dict[str, Any]:
    """One schema document keyed by item type, with `$defs` shared across them."""
    defs: dict[str, Any] = {}
    out: dict[str, Any] = {}
    for t in types:
        s = slot_schema(t)
        defs.update(s.pop("$defs", {}))
        out[t] = s
    if defs:
        out["$defs"] = defs
    return out


def canonical_json(obj: Any) -> str:
    """Stable text for hashing and for golden-file snapshots."""
    return json.dumps(obj, indent=2, sort_keys=True, ensure_ascii=False)
