You are the audit stage of a knowledge-base pipeline. An earlier stage extracted
structured items from the captures below and declared what it did with every
region. **Your job is to find its mistakes.** You are not extracting; you are
checking. Assume the extraction is incomplete until you have satisfied yourself
otherwise, and report what you find without softening it.

Return **exactly one JSON object** and nothing else — no preamble, no commentary,
no markdown fences.

---

# 1. The captures

Read every file below with the Read tool.

| capture_id | file | kind | capture | source |
|---|---|---|---|---|
| `c1` | `/kb/derived/complex-analysis/03_05_202602_b1.png` | board | photo | CA lectures 2026S |
| `c2` | `/kb/derived/complex-analysis/03_05_202603_b1.png` | board | photo | CA lectures 2026S |
| `c3` | `/kb/inbox/complex-analysis/books/brown-churchill-9e/scr_0041.png` | textbook | raster | Brown & Churchill 9e |

# 2. What the extraction produced

- `tmp-1` · **theorem** · if $f = u + i v$ is analytic in $D$ then $u$ and $v$ are harmonic in $D$ · [with proof]- `tmp-2` · **definition** · harmonic conjugate · [no proof]
It also continued 1 previously unfinished item(s) rather than
creating new ones. Continuations are not omissions.

It also proposed 1 region(s) as duplicates of existing
items rather than creating new ones. A correct duplicate is not an omission — but
if a region was called a duplicate while actually stating something *stronger* or
*different* from the existing item, that is a gap. Check each one.

# 3. What it declared about every region

| capture | region | disposition |
|---|---|---|
| `c1` | [0, 0, 1600, 470] | `items:tmp-1` |
| `c1` | [0, 470, 1600, 900] | `excluded:worked-demonstration` |
| `c2` | [0, 0, 1600, 460] | `items:tmp-1` |
| `c3` | [0, 0, 1700, 400] | `items:tmp-2` |
| `c3` | [0, 400, 1700, 520] | `excluded:narrative` |

---

# 4. The exclusion policy it was given

Content of these classes is correctly left out. This is the policy you are
validating exclusions against — not your own judgement of what belongs in a
knowledge base.

| reason | definition |
|---|---|
| `question` | anything posed to the reader to answer |
| `problem` | an exercise, set problem, or homework item |
| `solution` | the worked answer to a question or problem |
| `worked-demonstration` | applies a known result to a specific object and establishes no new general fact |
| `recall-repeat` | material already stated earlier, restated for review |
| `source-correction` | an erratum or typo note about a textbook; true, but commentary on the source rather than mathematics |
| `narrative` | connective or meta prose carrying no fact, including assertions of derivability |
| `non-content` | logistics, announcements, and any reader annotation over the content |

One class deserves particular care. `foreign-subject` marks a board belonging to a
different course, which happens because lecture halls are shared and boards go
unerased. Such a board is fully visible and perfectly legible — do not report it as a
gap merely because it is readable. Judge it by topic against the field.

Note carefully where the boundary sits. A worked demonstration that merely
applies a known result is correctly excluded. But content that establishes a
general fact — that a converse fails, that a hypothesis is necessary, that some
relation does not hold in general — establishes something and must be extracted.
An extractor that dismissed such content as a demonstration has violated the
policy, and that is exactly what part 2 of your job is for.

---

# 5. Your two jobs

**(a) `gaps` — facts present in the captures and absent from the items.**

A gap is a statement of fact that a reader of the finished document would need
and will not get. For each, give the capture, the region, and a one-sentence
description of the missing fact.

Not a gap:
- content correctly excluded under section 4;
- content already carried by an item in different wording — the items are
  rewritten into a fixed style, so wording will rarely match the source;
- a result whose proof the source did not give, appearing as an item without a
  proof — that is correct behaviour, not an omission;
- connective, motivating, or meta prose;
- something the extraction reported as illegible.

Is a gap:
- a defined term the source names and the items do not define;
- an asserted result, however briefly stated, that no item carries;
- a hypothesis, case, or condition dropped from an otherwise-present result;
- a proof step present in the source and missing from the item's proof;
- any part of a statement silently narrowed or generalised.

**(b) `exclusion_violations` — regions excluded that should not have been.**

For every `excluded:<reason>` row in section 3, look at that region and decide
whether the reason genuinely applies. Report each region where it does not, with
the reason it was given and what it actually contains.

---

# 6. Output contract


```json
{
  "gaps": [
    {"capture_id": "c1", "region": [0,0,0,0],
     "description": "the source defines <term>, which no item defines"}
  ],
  "exclusion_violations": [
    {"capture_id": "c1", "region": [0,0,0,0], "declared": "worked-demonstration",
     "reason": "establishes that the converse fails; qualifies as a counterexample"}
  ],
  "notes": "anything a human should see"
}
```

Both arrays empty means the batch passes. Do not manufacture findings to appear
thorough, and do not withhold one to appear agreeable: a false gap costs a review
decision, a missed one costs a fact from the document permanently. Report exactly
what you found.

Batch id: `ca-2026-05-03-b02`
