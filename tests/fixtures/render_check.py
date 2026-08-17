"""Render both packs against the REAL 2026-05-03 lecture batch and audit the result."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
from knowledge_base.extract.prompts import audit_context, extraction_context, render

TAXONOMY = dict(
  types=[
    dict(key="definition",     note="introduces or names a concept"),
    dict(key="theorem",        note="a major or source-labelled result"),
    dict(key="lemma",          note="an auxiliary result used to prove another"),
    dict(key="proposition",    note="an asserted result, the default for unlabelled results"),
    dict(key="corollary",      note="a result following immediately from a previous one"),
    dict(key="axiom",          note="an assumed starting point"),
    dict(key="claim",          note="a local asserted fact"),
    dict(key="counterexample", note="establishes that a converse fails or a hypothesis is necessary"),
    dict(key="notation",       note="a symbol or writing convention being introduced"),
    dict(key="remark",         note="a qualitative or contextual fact worth keeping"),
  ],
  excluded=[
    dict(key="question",  definition="anything posed to the reader to answer"),
    dict(key="problem",   definition="an exercise, set problem, or homework item"),
    dict(key="solution",  definition="the worked answer to a question or problem"),
    dict(key="worked-demonstration", definition="applies a known result to a specific object and establishes no new general fact"),
    dict(key="recall-repeat", definition="material already stated earlier, restated for review"),
    dict(key="source-correction", definition="an erratum or typo note about a textbook; true, but commentary on the source rather than mathematics"),
    dict(key="narrative", definition="connective or meta prose carrying no fact, including assertions of derivability"),
    dict(key="non-content", definition="logistics, announcements, and any reader annotation over the content"),
  ])

CAPTURES = [
  dict(id="c1", path="/kb/derived/complex-analysis/03_05_202602_b1.png",
       kind="board", capture="photo", source_title="CA lectures 2026S", page=None),
  dict(id="c2", path="/kb/derived/complex-analysis/03_05_202603_b1.png",
       kind="board", capture="photo", source_title="CA lectures 2026S", page=None),
  dict(id="c3", path="/kb/inbox/complex-analysis/books/brown-churchill-9e/scr_0041.png",
       kind="textbook", capture="raster", source_title="Brown & Churchill 9e", page=None),
]

SCHEMAS = {
  "definition": {"type":"object","required":["term","form","article","body"],
    "properties":{"term":{"type":"string"},"form":{"enum":["noun","predicate"]},
      "article":{"enum":["a","an","the","none"]},"subject":{"type":["string","null"]},
      "scope":{"type":["string","null"]},"context":{"type":["string","null"]},
      "body":{"type":"string"}}},
  "theorem": {"type":"object","required":["citation_form","hypotheses","conclusion","proofs"],
    "properties":{"citation_form":{"type":"string"},
      "hypotheses":{"type":"array","items":{"type":"string"}},
      "conclusion":{"type":"string"},"proofs":{"type":"array"},
      "converse_holds":{"enum":["true","false","unknown",None]}}},
}

ctx = extraction_context(
  batch_id="ca-2026-05-03-b02", field=dict(key="complex-analysis", title="Complex Analysis"),
  source=dict(key="brown-churchill-9e", conventions=(
      "Bold-italic marks a term being defined. Results are referred to by "
      "display-equation number in parentheses. Many proofs are deferred to exercises.")),
  captures=CAPTURES, taxonomy=TAXONOMY, schemas=SCHEMAS,
  lexicon=dict(canonical=["analytic","harmonic","harmonic conjugate","domain","entire"],
               banned={"analytic":["holomorphic","regular"],
                       "domain of definition":["domain (of a function)"],
                       "non-zero":["nonzero"]}),
  symbols=[dict(form="$overline(z)$", note="complex conjugate; never $z^*$"),
           dict(form="$op(\"Res\")_(z = z_0) f(z)$", note="residue"),
           dict(form="$nabla^2 u = 0$", note="Laplace's equation, when naming it"),
           dict(form="$u_(x x)$", note="partial derivatives, always subscript")],
  style_rules=["the word \"we\", in any phrase or position",
               "\"so\", \"thus\", \"hence\", \"it follows that\" as logical connectives",
               "\"clearly\", \"obviously\", \"trivially\", \"one can show\", \"it is easy to see\"",
               "\"i.e.\" and \"e.g.\" — write \"that is\" and \"for example\"",
               "\"harmonic on $D$\" — always \"harmonic in $D$\"",
               "\"holomorphic\" — always \"analytic\""],
  open_items=[dict(id="01J9XA", type="theorem", title=None,
                   missing="proof has steps but no conclusion; last capture ended mid-argument")],
  item_index=[dict(id="01J9XB", type="definition", title=None, digest="a domain is a nonempty open connected set"),
              dict(id="01J9XA", type="theorem", title=None, digest="the real and imaginary parts of an analytic function are harmonic")],
  identifier_table=[dict(identifier="Theorem 1", id="01J9XA", title=None),
                    dict(identifier="Sec. 26", id="01J9XB", title=None)],
  trailing_items=[dict(type="definition", digest="harmonic: has continuous second partials and satisfies Laplace's equation")],
)
ex_text, ex_hash = render("extract.md.j2", ctx)

au = audit_context(
  batch_id="ca-2026-05-03-b02", captures=CAPTURES, excluded=TAXONOMY["excluded"],
  items=[dict(tmp_id="tmp-1", type="theorem", title=None, has_proof=True,
              statement="if $f = u + i v$ is analytic in $D$ then $u$ and $v$ are harmonic in $D$"),
         dict(tmp_id="tmp-2", type="definition", title=None, has_proof=False,
              statement="harmonic conjugate")],
  coverage=[dict(capture_id="c1", region=[0,0,1600,470], disposition="items:tmp-1"),
            dict(capture_id="c1", region=[0,470,1600,900], disposition="excluded:worked-demonstration"),
            dict(capture_id="c2", region=[0,0,1600,460], disposition="items:tmp-1"),
            dict(capture_id="c3", region=[0,0,1700,400], disposition="items:tmp-2"),
            dict(capture_id="c3", region=[0,400,1700,520], disposition="excluded:narrative")],
  fragments=[dict(continues="01J9XA")], duplicates=[dict(tmp_id="tmp-2", of="01J9XB")])
au_text, au_hash = render("audit.md.j2", au)

open(Path(__file__).parent / "rendered_extract.md","w").write(ex_text)
open(Path(__file__).parent / "rendered_audit.md","w").write(au_text)
for name, t, h in (("extract", ex_text, ex_hash), ("audit", au_text, au_hash)):
    print(f"{name:8} {len(t):>6} chars  ~{len(t)//4:>5} tokens  hash={h}")

# determinism + leak checks
assert render("extract.md.j2", ctx)[0] == ex_text, "render is not deterministic"
for name, t in (("extract", ex_text), ("audit", au_text)):
    assert "{{" not in t and "{%" not in t, f"{name}: unrendered Jinja"
    assert "Undefined" not in t, f"{name}: undefined leaked"
    assert "{ref:ID}" in t or name == "audit", "STG ref token mangled"
print("checks: deterministic · no unrendered tags · no undefined leaks")
