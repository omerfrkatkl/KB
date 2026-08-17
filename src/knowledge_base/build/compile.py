"""Compiling and querying with the vendored toolchain (§I-11, §I-8 step 9).

Builds always use the pinned binary and `--font-path fonts/`. Zero dependence on
system state is not fussiness: a font substituted five years from now would
change every line break on every page, and nothing would report it.

`smoke` is validation step 9 — one item, emitted standalone, compiled. It catches
dialect and escaping bugs at the item that caused them rather than at a book
build where the compiler error points at line 4,000 of a generated file.
"""

from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass
from pathlib import Path

from knowledge_base.config import ROOT
from knowledge_base.ops.log import get

log = get("compile")

TYPST = ROOT / "tools" / "typst"
FONTS = ROOT / "fonts"


class ToolchainMissing(RuntimeError):
    """The vendored compiler is absent. Hard stop 3 — run `make bootstrap`."""


@dataclass
class CompileResult:
    ok: bool
    pdf: Path | None
    stderr: str


def available(root: Path = ROOT) -> bool:
    return (Path(root) / "tools" / "typst").exists()


def _binary(root: Path) -> Path:
    typst = Path(root) / "tools" / "typst"
    if not typst.exists():
        raise ToolchainMissing(
            "tools/typst is missing — run `make bootstrap`. Never fall back to a "
            "system typst: the build must be reproducible for decades.")
    return typst


def compile_doc(source: Path, root: Path = ROOT, out: Path | None = None) -> CompileResult:
    typst = _binary(root)
    pdf = out or source.with_suffix(".pdf")
    r = subprocess.run(
        [str(typst), "compile", "--font-path", str(Path(root) / "fonts"),
         str(source), str(pdf)],
        capture_output=True, text=True, cwd=source.parent)
    if r.returncode != 0:
        log.error("compile failed: %s", r.stderr.strip()[:2000])
        return CompileResult(ok=False, pdf=None, stderr=r.stderr)
    return CompileResult(ok=True, pdf=pdf, stderr="")


def query(source: Path, selector: str, root: Path = ROOT) -> list[dict]:
    typst = _binary(root)
    r = subprocess.run(
        [str(typst), "query", "--font-path", str(Path(root) / "fonts"),
         str(source), selector],
        capture_output=True, text=True, cwd=source.parent)
    if r.returncode != 0:
        raise RuntimeError(f"typst query failed: {r.stderr}")
    return json.loads(r.stdout)


def smoke(body: str, work: Path, template: Path, symbols: str = "",
          root: Path = ROOT) -> CompileResult:
    """Validation step 9: compile one item standalone."""
    work.mkdir(parents=True, exist_ok=True)
    (work / template.name).write_bytes(template.read_bytes())
    if symbols:
        (work / "symbols-gen.typ").write_text(symbols, encoding="utf-8")
    source = work / "smoke.typ"
    source.write_text(
        f'#import "{template.name}": *\n'
        + ('#import "symbols-gen.typ": *\n' if symbols else "")
        + '#show: project.with(title: "smoke", date: none)\n\n'
        + body + "\n",
        encoding="utf-8")
    return compile_doc(source, root=root)
