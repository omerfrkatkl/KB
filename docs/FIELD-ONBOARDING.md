# Onboarding a field

What "one-time setup per subject" concretely means. Written from building the
machinery rather than from running it end to end, so the steps that have been
executed are marked and the ones that have not are marked too — a runbook that
does not say which is which is worse than none.

The test of this document is WP5.2: onboarding ODE must require **no core code
change**. Anything that does is a defect in core, not a gap here.

---

## 0. Before anything

- `make bootstrap` — the pinned toolchain. ✅ executed
- `make check` — green from a clean clone. ✅ executed
- `make rules` — compile `rules/` into `generated/`. ✅ executed

`make rules` runs **before any extraction, always**. Compiling the rule
documents converts terminology rulings into decisions already made; each one is
a `new-term` queue entry that never happens. This is the single largest reducer
of runtime interruption and it is not optional.

---

## 1. Author the field rule document

`rules/fields/<field>.txt`, roughly the length of `rules/fields/ode.txt`
(≈500 lines). It is the only authored input that cannot be derived from
anything else.

Precedence is fixed: **field file > Proof_Style > Common**. Write the field
document to state what is *different* about this subject, and let the shared
documents carry the rest. Restating a Common rule in a field file creates two
owners for one rule, which is the defect the 2026-07-29 edit pass removed.

Write terminology rulings in the shape the compiler reads with confidence:

    ALWAYS "<canonical>" — NEVER "<variant>" or "<variant>".

One sentence, an em dash, both sides quoted. That shape compiles straight into
an automatic substitution. A ruling spread over two sentences still reaches the
owner — it lands in `generated/lexicon/<field>.candidates.yaml` with the
sentence it came from — but it is *not enforced* until ruled on. See
`src/knowledge_base/rules/parse.py` for why the looser shapes are refused.

Two shapes that will never auto-substitute, by design:

- a variant that is part of a mandated term (`entire` inside "an entire
  function"), which would rewrite its own replacement;
- a variant that occurs inside another canonical term (`transformation` inside
  "linear fractional transformation"), which would corrupt a proper name.

Both are real rules; both need a human ruling rather than a regex.

## 2. Compile and spot-check

    make rules
    knowledge-base status        # reports the ruling count per field

Read 20 entries of `generated/lexicon/<field>.yaml` against the document. This
is the WP1.4A definition of done and it takes about ten minutes. Then skim
`generated/lexicon/<field>.candidates.yaml`: for Complex Analysis this is
around 60 proposals, most of which are correct and none of which are enforced.

## 3. Author the profile

`fields/<field>/profile/`:

| File | Authored how |
|---|---|
| `taxonomy.yaml` | copy another field's and change nothing unless the subject genuinely needs a different type set. It is the emitter allowlist; widening it is a real decision. |
| `sources.yaml` | left empty. The new-source queue fills it at first ingestion. |
| `outline.yaml` | from the textbook's table of contents, in the same pass as source registration. Approved once (A5). |
| `symbols.yaml` | `#let` bindings, seeded from the field document's notation sections. Optional; the template already defines `Re/Im/Arg/Log/Res`. |

Register sources and author the outline **before** ingesting. Each is a queue
that then stays empty.

## 4. Add the field to `config.yaml`

```yaml
fields:
  <field-key>:
    title: "<Title as it appears on the PDF>"
    captures: "Mathematics/10-Source-Captures/<Drive-Folder>"
```

and add the field key to `FIELD_DOCS` in
`src/knowledge_base/rules/compile_rules.py` so its rule document compiles.

> This is the one core-code touch onboarding currently needs. It is a one-line
> mapping and a candidate for moving into `config.yaml` in WP5.2 — noting it
> here rather than fixing it speculatively.

## 5. Calibration batch

    knowledge-base ingest <field>
    knowledge-base extract <field> --limit 1
    knowledge-base validate <field>
    knowledge-base review

Expect the first batch to be flag-heavy. That is the calibration working: the
`new-term` queue is at its densest before the first ruling sitting and thins
sharply afterwards. Judge the batch on whether the *flags are right*, not on how
many there are.

## 6. First build

    knowledge-base build <field>

Read the PDF end to end and accept every item, or file the deltas as rulings and
schema extensions. Schema changes are **extend-only** (A7): add a field or a
variant, never repurpose one.

Then `knowledge-base relint` so the sitting's rulings reach the items already
stored. Consistency across time is what relint is for; without it the corpus is
consistent only forward of the ruling.

---

## Expected flag density

**Not yet measured.** It needs a real calibration batch, and no extraction has
been performed by this system (`docs/FINDINGS.md`). Record the numbers
here after the first one:

| Field | Batch size | new-term | unclassified | near-duplicate | pending-ref |
|---|---|---|---|---|---|
| complex-analysis | — | — | — | — | — |
| ordinary-differential-equations | — | — | — | — | — |

## What is not onboarding

Adding a **subject** is this document. Adding a **source** to an existing field
is one queue entry answered once — title, citation, rank, and the typographic
`conventions` block that then travels in that source's prompts. Do not confuse
the two: a second Complex Analysis textbook is not a new field.
