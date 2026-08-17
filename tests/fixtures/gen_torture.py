"""Emission plan -> torture.typ. Seed of the real emitter; shared by test_parity."""
from knowledge_base.build.numbering_sim import simulate

ESCAPES = list('\\#$[]{}@*_`<>~')  # backslash first
def esc(text: str) -> str:
    for ch in ESCAPES:
        text = text.replace(ch, '\\' + ch)
    return text.replace('//', '/\\/')

FN = {"thm":"thm","def":"def","lem":"lem","prop":"prop","cor":"cor",
      "axiom":"axiom","claim":"claim","remark":"remark","notation":"notation"}

PLAN = [
 {"kind":"heading","title":"Alpha"},
 {"kind":"item","key":"def","numbered":True,"body":"A holomorphic thing is a thing."},
 {"kind":"item","key":"thm","numbered":True,"star":True,"title":"Rouché's Theorem",
  "body":"Suppose the hypotheses hold. Then the conclusion holds.","proof":True},
 {"kind":"item","key":"remark","numbered":False,"star":True,
  "body":"Nasty escaping: 5 # $ [ ] { } @ * _ ` < > ~ 1/2 // end.","escape":True},
 {"kind":"item","key":"claim","numbered":True,
  "body":"The converse of REFPREV is false: a witness exists."},
 {"kind":"item","key":"notation","numbered":False,"body":"One writes x = (x, 0)."},
 {"kind":"item","key":"lem","numbered":True,"body":"A small stepping stone."},
 {"kind":"heading","title":"Beta"},
 {"kind":"item","key":"prop","numbered":True,"body":"Counter reset check: expect 2.1."},
 {"kind":"item","key":"cor","numbered":True,"body":"Follows from the proposition. Long body. " + "Pagination filler sentence. "*40},
 {"kind":"heading","title":"Gamma"},
 {"kind":"item","key":"axiom","numbered":True,"body":"A starting point.","star":True},
 {"kind":"item","key":"thm","numbered":True,"body":"Back-reference check: see REFBACK and forward none."},
]

def generate(plan_solved):
    lines = ['#import "template-star.typ": *',
             '#show: project.with(title: "Torture", authors: ("parity",), date: none)','']
    # resolve internal ref placeholders
    first_thm = next(e["label"] for e in plan_solved if e.get("key")=="thm" and e.get("label"))
    for e in plan_solved:
        if e["kind"] == "heading":
            lines += [f'= {e["title"]}']
            continue
        body = e["body"].replace("REFPREV", f"@{first_thm}").replace("REFBACK", f"@{first_thm}")
        if e.get("escape"):
            body = esc(e["body"])
        args = []
        if e.get("title"):
            args.append(f'title: [{e["title"]}]')
        if e.get("star"):
            args.append("star: true")
        arg = (", ".join(args))
        call = f'#{FN[e["key"]]}({arg})[{body}]' if arg else f'#{FN[e["key"]]}[{body}]'
        lines.append(call)
        if e.get("proof"):
            lines.append('#proof[By hypothesis, the claim holds. '
                         'A direct computation gives $ z_1 + z_2 = z_2 + z_1 $. '
                         'Therefore the conclusion holds.]')
    return "\n".join(lines) + "\n"

if __name__ == "__main__":
    solved = simulate(PLAN)
    open("torture.typ","w").write(generate(solved))
    print("expected labels:", [e["label"] for e in solved if e.get("label")])
