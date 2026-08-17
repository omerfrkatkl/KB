"""Parity: the numbering simulation must equal what typst actually assigns.

Requires typst on PATH; skipped otherwise so a fresh clone reports a clean suite
rather than a spurious failure.
"""
import json
import shutil
import subprocess
from pathlib import Path

import pytest
from gen_torture import PLAN, generate

from knowledge_base.build.numbering_sim import simulate
from knowledge_base.ops.bootstrap import find_typst

ROOT = Path(__file__).resolve().parents[1]
TYPST = find_typst()
FONTS = ROOT / "fonts"
FIXTURES = ROOT / "tests" / "fixtures"
pytestmark = pytest.mark.skipif(
    TYPST is None, reason="typst is not installed or not on PATH")

def test_numbering_parity(tmp_path):
    solved = simulate(PLAN)
    shutil.copy(ROOT / "template" / "template-star.typ", tmp_path)
    doc = tmp_path / "torture.typ"
    doc.write_text(generate(solved), encoding="utf-8", newline="")

    c = subprocess.run([str(TYPST), "compile", "--font-path", str(FONTS), str(doc)],
                       capture_output=True, text=True, cwd=tmp_path)
    assert c.returncode == 0, f"compile failed:\n{c.stderr}"

    q = subprocess.run([str(TYPST), "query", "--font-path", str(FONTS), str(doc),
                        'figure.where(kind: "math-env")'],
                       capture_output=True, text=True, cwd=tmp_path)
    els = json.loads(q.stdout)

    def sup(e):
        s = e["supplement"]
        return (s or {}).get("text") if isinstance(s, dict) else s
    actual = [(sup(e), e["label"].strip("<>") if e.get("label") else None) for e in els]
    names = {"thm":"Theorem","def":"Definition","lem":"Lemma","prop":"Proposition",
             "cor":"Corollary","axiom":"Axiom","claim":"Claim","remark":"Remark",
             "notation":"Notation"}
    expected = [(names[e["key"]], e["label"]) for e in solved if e["kind"] == "item"]
    assert actual == expected, f"PARITY MISMATCH\nexpected={expected}\nactual={actual}"
    assert all(e["label"] is None for e in solved
               if e["kind"] == "item" and not e["numbered"]), "unnumbered must be label-free"
