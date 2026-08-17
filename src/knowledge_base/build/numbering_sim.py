"""Numbering/label simulation for the notes template.

Empirically verified facts (2026-07-20, typst 0.15.1, real template):
- unnumbered math-envs do NOT advance the shared counter (unnumbered_advances=False)
- level-1 headings reset the counter; numbered label = f"{key}-{section}.{n}"
- unnumbered envs carry no label
"""
UNNUMBERED_ADVANCES = False  # resolved: B5

def simulate(plan):
    """plan: list of events.
    {"kind":"heading"} | {"kind":"item","key":str,"numbered":bool,...}
    Returns plan copy with 'label' (str|None) and 'number' (str|None) filled."""
    section, n = 0, 0
    out = []
    for ev in plan:
        ev = dict(ev)
        if ev["kind"] == "heading":
            section += 1
            n = 0
        elif ev["kind"] == "item":
            if ev.get("numbered", True):
                n += 1
                num = f"{section}.{n}" if section > 0 else str(n)
                ev["number"] = num
                ev["label"] = f'{ev["key"]}-{num}'
            else:
                if UNNUMBERED_ADVANCES:
                    n += 1
                ev["number"] = None
                ev["label"] = None
        out.append(ev)
    return out
