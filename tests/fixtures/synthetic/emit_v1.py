"""SYNTHETIC demonstration: hand-written Complex Analysis items → Typst.

NOT extracted from any source. The provenance photo references below are
fabricated placeholders retained only so the emitter exercises that code path.

Every item: provenance kind=board (session 2026-05-03) => exam_star derives TRUE.
This set is a renderer regression fixture only — see docs/FINDINGS.md,
"What is not evidence".
Math dialect: typst (config default; runtime-model fluency = B13, still open).
"""
import sys

import yaml

sys.path.insert(0, "..")
import frames_v1 as frames
from numbering_sim import simulate

S = {"source": "ca-lectures-2026s", "kind": "board", "session": "2026-05-03"}
def prov(photos): return [dict(S, photo=f"03_05_2026{p:02d}.jpeg") for p in photos]

ITEMS = [
 # ── review board ("Last Time", photo 1 left) — prior-lecture content, first occurrence in store
 dict(id="conn", type="definition", topic="regions", provenance=prov([1]),
      slots=dict(form="predicate", subject="A set $S$", term="connected",
                 body="it cannot be expressed as the union of two disjoint nonempty open sets")),
 dict(id="dom", type="definition", topic="regions", provenance=prov([1]),
      slots=dict(form="noun", article="a", term="domain",
                 body="a nonempty open connected set")),
 dict(id="poly", type="proposition", topic="regions", provenance=prov([1]),
      slots=dict(citation_form="any two points of a domain are joined by a polygonal path lying in that domain",
                 hypotheses=["$D$ is a domain", "$z_1, z_2 in D$"],
                 conclusion="there is a polygonal path from $z_1$ to $z_2$ lying in $D$",
                 proofs=[])),
 # ── new content: harmonic functions
 dict(id="harm", type="definition", topic="harmonic", provenance=prov([1]),
      slots=dict(form="predicate", context="$D$ be a domain",
                 subject="A function $u(x, y)$", term="harmonic", scope="on $D$",
                 body="it has continuous partial derivatives of the first and second order in $D$ and satisfies Laplace's equation in $D$")),
 dict(id="lapl", type="definition", topic="harmonic", provenance=prov([1]),
      slots=dict(form="noun", article="none", term="Laplace's equation",
                 body="the equation $nabla^2 u = 0$")),
 dict(id="anal-harm", type="theorem", topic="harmonic", provenance=prov([2, 3]),
      title=None,
      slots=dict(citation_form="the real and imaginary parts of an analytic function are harmonic in its domain",
                 hypotheses=["$f(z) = u(x, y) + i v(x, y)$ is analytic in a domain $D$"],
                 conclusion="$u$ and $v$ are harmonic in $D$",
                 proofs=[dict(method="direct", steps=[
                   dict(claim="$u$ and $v$ have continuous partial derivatives of all orders in $D$",
                        justification=dict(kind="by-fact", fact="an analytic function has derivatives of all orders")),
                   dict(claim="$u_x = v_y$ and $u_y = -v_x$ in $D$",
                        justification=dict(kind="by-fact", fact="the Cauchy–Riemann equations hold in $D$")),
                   dict(claim="$u_(x x) = v_(y x)$ and $u_(y y) = -v_(x y)$",
                        justification=dict(kind="by-computation")),
                   dict(claim="$v_(x y) = v_(y x)$",
                        justification=dict(kind="by-fact", fact="the mixed partial derivatives of $v$ are continuous")),
                   dict(claim="$u$ is harmonic in $D$",
                        justification=dict(kind="by-previous-step")),
                   dict(claim="$v$ is harmonic in $D$",
                        justification=dict(kind="by-computation")),
                 ], conclusion="$u$ and $v$ are harmonic in $D$")])),
 dict(id="hconj", type="definition", topic="harmonic", provenance=prov([4, 9]),
      slots=dict(form="predicate", context="$u$ and $v$ be functions on a domain $D$",
                 subject="The function $v$", term="harmonic conjugate", scope="of $u$ in $D$",
                 body="$u$ and $v$ are harmonic in $D$ and their first-order partial derivatives satisfy the Cauchy–Riemann equations $u_x = v_y$ and $u_y = -v_x$")),
 dict(id="iff", type="theorem", topic="harmonic", provenance=prov([4, 9]),
      slots=dict(citation_form="a function is analytic in a domain if and only if its imaginary part is a harmonic conjugate of its real part there",
                 hypotheses=["$f(z) = u(x, y) + i v(x, y)$ is defined on a domain $D$"],
                 conclusion="$f$ is analytic in $D$ if and only if $v$ is a harmonic conjugate of $u$ in $D$",
                 proofs=[dict(method="iff-pair",
                   forward=[
                     dict(claim="$u$ and $v$ are harmonic in $D$",
                          justification=dict(kind="by-ref", ref="anal-harm")),
                     dict(claim="the Cauchy–Riemann equations hold in $D$",
                          justification=dict(kind="by-fact", fact="$f$ is analytic")),
                   ],
                   backward=[
                     dict(claim="$f$ is analytic in $D$",
                          justification=dict(kind="by-fact",
                            fact="the Cauchy–Riemann equations hold and the first-order partial derivatives of $u$ and $v$ are continuous")),
                   ],
                   forward_conclusion="$v$ is a harmonic conjugate of $u$ in $D$",
                   conclusion="$f$ is analytic in $D$ if and only if $v$ is a harmonic conjugate of $u$ in $D$")])),
 dict(id="nonsym", type="claim", topic="harmonic", provenance=prov([5]),
      slots=dict(citation_form="being a harmonic conjugate is not a symmetric relation",
                 body="being a harmonic conjugate is not a symmetric relation: there exist $u, v$ such that $v$ is a harmonic conjugate of $u$ but $u$ is not a harmonic conjugate of $v$",
                 proofs=[dict(method="construction", setup="the pair $u = x^2 - y^2$, $v = 2 x y$", steps=[
                   dict(claim="$v$ is a harmonic conjugate of $u$ in $CC$",
                        justification=dict(kind="by-fact", fact="$f(z) = z^2 = (x^2 - y^2) + i(2 x y)$ is analytic in $CC$")),
                   dict(claim="$g = 2 x y + i(x^2 - y^2)$ fails the Cauchy–Riemann equations off the origin",
                        justification=dict(kind="by-computation")),
                   dict(claim="$g$ is not analytic in any domain",
                        justification=dict(kind="by-ref", ref="iff")),
                 ], conclusion="the relation is not symmetric")])),
 dict(id="sc-exist", type="proposition", topic="harmonic", provenance=prov([5, 7]),
      slots=dict(citation_form="a function harmonic in a simply connected domain has a harmonic conjugate there",
                 hypotheses=["$u$ is harmonic in a simply connected domain $D$"],
                 conclusion="$u$ has a harmonic conjugate in $D$", proofs=[])),
 dict(id="no-hc", type="claim", topic="harmonic", provenance=prov([5]),
      slots=dict(citation_form="a harmonic function need not have a harmonic conjugate in its domain",
                 body="there exist a domain $D$ and a function $u$ harmonic in $D$ such that $u$ has no harmonic conjugate in $D$",
                 proofs=[])),
 dict(id="uniq", type="theorem", topic="harmonic", provenance=prov([7]),
      slots=dict(citation_form="two harmonic conjugates of the same function differ by a constant",
                 hypotheses=["$v_1$ and $v_2$ are harmonic conjugates of $u$ in a domain $D$"],
                 conclusion="$v_1 - v_2$ is constant in $D$",
                 proofs=[dict(method="direct", steps=[
                   dict(claim="$(v_1)_y = u_x = (v_2)_y$ and $(v_1)_x = -u_y = (v_2)_x$",
                        justification=dict(kind="by-definition", term="harmonic conjugate", ref="hconj")),
                   dict(claim="$nabla (v_1 - v_2) = 0$ in $D$",
                        justification=dict(kind="by-computation")),
                   dict(claim="$v_1 - v_2$ is constant in $D$",
                        justification=dict(kind="by-fact", fact="a function with vanishing gradient in a domain is constant")),
                 ], conclusion="the two conjugates differ by a constant")])),
 dict(id="orth", type="theorem", topic="harmonic", provenance=prov([8]),
      slots=dict(citation_form="the level curves of the real and imaginary parts of an analytic function are orthogonal at every point where the derivative is non-zero",
                 hypotheses=["$f = u + i v$ is analytic in a domain $D$",
                             "$z_0 in D$ and $f'(z_0) != 0$"],
                 conclusion="the level curves $u(x, y) = c_1$ and $v(x, y) = c_2$ through $z_0$ intersect orthogonally at $z_0$",
                 proofs=[dict(method="direct", steps=[
                   dict(claim="$nabla u dot nabla v = u_x v_x + u_y v_y$",
                        justification=dict(kind="by-computation")),
                   dict(claim="$nabla u dot nabla v = u_x (-u_y) + u_y u_x = 0$",
                        justification=dict(kind="by-fact", fact="the Cauchy–Riemann equations hold")),
                   dict(claim="$nabla u (z_0) != 0$ and $nabla v (z_0) != 0$, and both level curves are smooth at $z_0$ with normal vectors $nabla u (z_0)$ and $nabla v (z_0)$",
                        justification=dict(kind="by-fact",
                          fact="$abs(f')^2 = u_x^2 + u_y^2 = v_x^2 + v_y^2$ and $f'(z_0) != 0$")),
                   dict(claim="the normal vectors are orthogonal at $z_0$",
                        justification=dict(kind="by-previous-step")),
                 ], conclusion="the level curves intersect orthogonally at $z_0$")])),
 dict(id="mvp", type="theorem", topic="harmonic", provenance=prov([9]),
      slots=dict(citation_form="the value of a harmonic function at a point is the mean of its values on any sufficiently small circle centred at that point",
                 hypotheses=["$u$ is harmonic in a domain $D$", "$z_0 in D$"],
                 conclusion="$u(z_0) = 1/(2 pi) integral_0^(2 pi) u(z_0 + r e^(i theta)) dif theta$ for all sufficiently small $r > 0$",
                 proofs=[])),
]

OUTLINE = [("Regions in the Complex Plane", ["conn", "dom", "poly"]),
           ("Harmonic Functions", ["harm", "lapl", "anal-harm", "hconj", "iff",
                                    "nonsym", "sc-exist", "no-hc", "uniq", "orth", "mvp"])]

FN = {"definition": "def", "theorem": "thm", "proposition": "prop", "claim": "claim"}

def build_plan():
    plan, order = [], []
    by_id = {it["id"]: it for it in ITEMS}
    for title, ids in OUTLINE:
        plan.append({"kind": "heading", "title": title})
        for i in ids:
            it = by_id[i]
            plan.append({"kind": "item", "key": FN[it["type"]], "numbered": True, "id": i})
            order.append(it)
    return plan, order

def emit():
    plan, order = build_plan()
    solved = simulate(plan)
    label = {e["id"]: e["label"] for e in solved if e.get("id")}

    def reflink(rid):
        return f"@{label[rid]}"

    global DOC
    DOC = frames.Doc({i["id"]: i for i in ITEMS}, [i["id"] for i in ITEMS])
    lines = ['#import "template-star.typ": *',
             '#show: project.with(title: "Complex Analysis — Rule-Compliant Slice",',
             '  authors: ("KB pipeline · vertical slice",), date: "3 May 2026 lecture")', ""]
    by_id = {it["id"]: it for it in ITEMS}
    for e in solved:
        if e["kind"] == "heading":
            lines += [f'= {e["title"]}', ""]
            continue
        it = by_id[e["id"]]
        body = (frames.definition(it) if it["type"] == "definition"
                else frames.claim_body(it) if it["type"] == "claim"
                else frames.statement(it))
        star = "star: true"  # derived: every provenance entry is kind=board
        lines.append(f'#{FN[it["type"]]}({star})[{body}]')
        for pf in it["slots"].get("proofs", []):
            lines.append(f"#proof[{frames.render_proof(pf, DOC, it)}]")
        lines.append("")
    return "\n".join(lines), label

if __name__ == "__main__":
    typ, label = emit()
    open("main.typ", "w", encoding="utf-8", newline="").write(typ)
    yaml.safe_dump({"items": ITEMS, "outline": OUTLINE},
                   open("items.yaml", "w", encoding="utf-8", newline=""),
                   allow_unicode=True, sort_keys=False)
    print("emitted", len(ITEMS), "items; labels:", ", ".join(label.values()))
