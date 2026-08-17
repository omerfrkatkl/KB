"""Regression tests for the prompt packs. Run under pytest in the real repo."""
import json
import re
from pathlib import Path

import render_check as rc  # tests/fixtures/, on sys.path via conftest

from knowledge_base.extract.prompts import HERE, render

FIX = Path(__file__).resolve().parent / "fixtures"
EX = FIX / "rendered_extract.md"
AU = FIX / "rendered_audit.md"

def test_renders_deterministically():
    a, ha = render("extract.md.j2", rc.ctx)
    b, hb = render("extract.md.j2", rc.ctx)
    assert a == b and ha == hb

def test_no_template_leaks():
    for f in (EX, AU):
        t = f.read_text(encoding="utf-8")
        assert "{{" not in t and "{%" not in t and "Undefined" not in t

def test_contract_blocks_are_valid_json():
    for f in (EX, AU):
        for blk in re.findall(r"```json\n(.*?)```", f.read_text(encoding="utf-8"), re.S):
            json.loads(re.sub(r"<[^>]*>", "x", re.sub(r'"<[^"]*>"', '"x"', blk)))

def test_every_contract_field_is_explained():
    t = EX.read_text(encoding="utf-8")
    for k in ["items","fragments","duplicates","unclassified","figures",
              "pending_refs","coverage","terms","notes"]:
        assert t.count(k) >= 2, k

def test_section_numbering_contiguous():
    ns = [int(n) for n in re.findall(r"^# (\d+)\. ", EX.read_text(encoding="utf-8"), re.M)]
    assert ns == list(range(1, len(ns) + 1))

def test_exclusion_vocabulary_shared():
    """The auditor validates the extractor's exclusions, so both must use one list."""
    pat = r"^\| `([a-z-]+)` \| "
    ex = set(re.findall(pat, EX.read_text(encoding="utf-8"), re.M))
    au = set(re.findall(pat, AU.read_text(encoding="utf-8"), re.M))
    shared = {"question","problem","solution","worked-demonstration",
              "recall-repeat","narrative","non-content"}
    assert shared <= ex and shared <= au

def test_load_bearing_rules_present():
    t = " ".join(EX.read_text(encoding="utf-8").split())
    for probe in ["never write a number into slot text",
                  "A forced fit is silent distortion",
                  "Fabricated rigor is worse",
                  "silent skipping is a failure",
                  "citation_form"]:
        assert probe in t, probe

def test_audit_is_adversarially_framed():
    t = " ".join(AU.read_text(encoding="utf-8").split())
    assert "find its mistakes" in t
    assert "Both arrays empty means the batch passes" in t
    assert "do not withhold one to appear agreeable" in t

def test_templates_are_lf_only():
    """prompt_hash (extract/prompts.py) hashes template bytes verbatim, so a CR
    byte in the checkout silently changes provenance across platforms. .gitattributes
    enforces LF for these files; this asserts the enforcement actually held."""
    for name in ("extract.md.j2", "audit.md.j2"):
        raw = (HERE / name).read_bytes()
        assert b"\r" not in raw, name

def test_conditional_blocks_respond_to_context():
    """Board and raster guidance must appear only when such captures are present."""
    pdf_only = dict(rc.ctx)
    pdf_only["captures"] = [dict(id="c1", path="/x.png", kind="textbook",
                                capture="pdf", source_title="BC9e", page=12)]
    pdf_only["has_board"] = False
    pdf_only["has_raster"] = False
    t, _ = render("extract.md.j2", pdf_only)
    assert "Physical position on the board" not in t
    assert "Never infer a page number" not in t
