# Prompt packs

Two templates, one assembler, one test suite. These are the only channel through
which policy reaches the probabilistic stage, so they are rendered from the same
artifacts that enforce policy downstream — never from a hand-maintained copy.

    extract.md.j2      extraction prompt (16 sections)
    audit.md.j2        coverage-audit prompt (6 sections)
    assemble.py        Jinja env, context builders, prompt_hash
    test_prompts.py    9 regression tests
    render_check.py    renders both against the real 2026-05-03 lecture batch
    rendered_*.md      those renders, for inspection

## Cost

Rendered against a realistic three-capture batch:

    extract   ~4,200 tokens
    audit     ~1,300 tokens

Roughly 5.5k tokens of instruction per batch, before image content. At 8 pages or
6 captures per batch this is a small fraction of the call, but it is not free and
it is the figure to watch if B3 (Pro usage limits) turns out tight — the item
index and trailing-context sections are the compressible parts.

## Design decisions worth knowing

**StrictUndefined.** A missing context variable raises rather than rendering a
blank section. A prompt that silently loses its exclusion policy would produce
plausible, wrong output for an entire batch; failing the call is strictly better.

**Conditional guidance.** Board-specific instructions (position carries no
meaning, ignore edge-clipped content) and raster-specific instructions (no page
number, may be a fragment, may overlap) render only when such captures are in the
batch. A PDF-only batch never sees them. Tested.

**One exclusion vocabulary.** The audit prompt validates the extractor's
exclusions, so both templates render the exclusion classes from the same
`taxonomy.excluded` list. A test asserts they agree; if they ever diverge, the
auditor would be checking against a policy the extractor was never given.

**The audit is adversarial on purpose.** It opens by telling the model its job is
to find the extraction's mistakes, and it closes by forbidding both manufactured
findings and withheld ones. Same-model blind spots (B9) remain the known weakness;
this framing is the mitigation, `kb spotcheck` is the backstop.

**Style rules are injected, not restated.** The forbidden-word list and notation
forms come from `generated/validators/<field>.yaml` and `generated/symbols/` —
the same artifacts the regex engine consumes. This is dual consumption of one
compiled artifact, not a second copy: telling the extractor the rules reduces
validation retries, while the engine still enforces them independently.

## Verified

- Both templates render deterministically; identical context ⇒ identical bytes and
  identical `prompt_hash`.
- Every JSON block in both rendered prompts parses as JSON.
- Every field in the output contract is explained in the body (this test caught
  two real omissions: `fragments` and an entirely missing figures section).
- Section numbering contiguous, 1–16.
- No unrendered Jinja tags, no undefined leaks.

## Not yet verified

The prompts have never been sent to the runtime model. Instruction-following,
schema adherence, and the true cost of the pack are all WP0.3 measurements
(B1, B2, B13, B16). Expect at least one revision after the first real batch —
the likely edits are compression of sections 10–13 if the pack proves expensive,
and sharpening of section 5's classification rubric if the proposition/theorem
default misfires.
