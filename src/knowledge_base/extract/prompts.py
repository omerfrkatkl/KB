"""prompts.py — deterministic prompt-pack assembly.

The pack is the ONLY channel through which policy reaches the extractor, so it is
assembled from the same artifacts that enforce policy downstream:
  taxonomy.yaml            -> types + exclusion classes (shared with the auditor)
  pydantic models          -> JSON Schemas (single source of truth, I-1)
  generated/lexicon/       -> canonical + banned terms
  generated/symbols/       -> notation forms
  generated/validators/    -> slot-content style rules, rendered as a digest
                              (dual consumption: regex engine + prompt)
prompt_hash = sha256(template bytes + rendered context digest) and is recorded in
every item's provenance, so any future quality question is traceable (I-1).
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, StrictUndefined

HERE = Path(__file__).resolve().parents[3] / "prompts"   # repo prompts/

def env() -> Environment:
    return Environment(
        loader=FileSystemLoader(HERE),
        undefined=StrictUndefined,      # a missing variable must fail loudly,
        trim_blocks=True,               # never render as a silent blank section
        lstrip_blocks=True,
        keep_trailing_newline=True,
    )

def render(template: str, ctx: dict) -> tuple[str, str]:
    tpl_src = (HERE / template).read_bytes()
    text = env().get_template(template).render(**ctx)
    digest = hashlib.sha256(
        tpl_src + json.dumps(ctx, sort_keys=True, default=str).encode()
    ).hexdigest()[:16]
    return text, digest

def extraction_context(*, batch_id, field, source, captures, taxonomy, schemas,
                       lexicon, symbols, style_rules, open_items, item_index,
                       identifier_table, trailing_items, dialect="typst") -> dict:
    return dict(
        batch_id=batch_id, field=field, source=source, captures=captures,
        taxonomy=taxonomy, schemas=json.dumps(schemas, indent=2, ensure_ascii=False),
        lexicon=lexicon, symbols=symbols, style_rules=style_rules,
        open_items=open_items, item_index=item_index,
        identifier_table=identifier_table, trailing_items=trailing_items,
        dialect=dialect,
        has_board=any(c["kind"] == "board" for c in captures),
        has_raster=any(c["capture"] == "raster" for c in captures),
    )

def audit_context(*, batch_id, captures, items, coverage, excluded,
                  fragments=(), duplicates=()) -> dict:
    return dict(batch_id=batch_id, captures=captures, items=items,
                coverage=coverage, excluded=excluded,
                fragments=list(fragments), duplicates=list(duplicates))
