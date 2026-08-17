# Autonomy protocol — how to run setup without asking

The owner says "start", provides the prepared resources, and does not want to be
consulted again until setup is complete. This file makes that achievable by
removing the two things that cause an agent to stop: an unanswered question, and
an ambiguous specification.

## The rule

**Never ask. Choose the documented default, record the choice, continue.**

Every decision this project can foresee has a default written down. When you meet
one, you do not raise it — you apply the default, append an entry to
`DECISIONS-TAKEN.md`, and carry on. The owner reviews that file afterwards. A
decision reviewed after the fact costs him five minutes; a decision that stops
the run costs him the unattended setup he asked for.

When you meet a decision that is *not* foreseen, you still do not ask. You apply
the **fallback ordering** below, log it as `UNFORESEEN`, and continue.

## Fallback ordering, for anything undocumented

1. **The rule documents win.** If `rules/` settles it, follow them.
2. **The plan wins next.** If `docs/implementation-plan.md` settles it, follow it.
3. **Prefer the reversible option.** Between two defensible choices, take the one
   that is cheaper to undo, and say so in the log.
4. **Prefer the option that preserves information.** Never discard, never
   force-fit, never overwrite an original. Flagging costs a review; silent loss
   is unrecoverable.
5. **Prefer the narrower scope.** Implement what is specified, not what might be
   wanted. An unbuilt feature is cheaper than a wrong one.

## The only three hard stops

Stop and report **only** for these. Everything else is a decision you take.

1. **A measurement contradicts the plan such that continuing would build on a
   false premise.** Example: the toolchain's numbering behaviour disagrees with
   `numbering_sim.py`. Do not paper over it; the parity guarantee is the point.
2. **Proceeding risks losing or corrupting the owner's originals.** Anything
   under `inbox/`, or anything that would rewrite Drive.
3. **A required resource cannot be obtained** and no substitute is specified —
   the pinned toolchain, the fonts, an authenticated CLI.

A failing test is not a hard stop; fix it. A gap in the spec is not a hard stop;
apply the ordering above. An extraction that produces poor results is not a hard
stop; record the score and continue — that measurement is the deliverable.

## Measurements are yours to take

Where the plan says a value is measured, measure it. Do not ask for it.

| Value | How to obtain it |
|---|---|
| `resolution_floor_px` | Median text height by connected-component analysis over the calibration captures; set the floor at the 5th percentile of frames judged readable, and record the distribution |
| `budget.max_pages_per_night` | Wall-clock and limit behaviour over one measured window; set to 70% of what was sustained |
| `batching.*` | Keep the defaults unless a batch exceeds the prompt's token budget; then reduce by two and re-measure |
| `dedup.auto_confirm`, `queue_floor` | Keep the conservative defaults; tuning requires the overlap trial and is explicitly deferred |
| `dialect` | The A/B in WP0.3 decides; if the results are within noise, keep `typst` — it removes a conversion layer |

## Interruption is designed out, not wished away

The review queues exist because the owner ruled that unclassifiable content must
never be force-fitted. They are correct and they stay. What must not happen is
their firing for things already decided. Therefore:

**`make rules` runs before any extraction, always.** Compiling `rules/` into
`generated/lexicon/` converts roughly 150 canonical/banned term pairs into
rulings that are already made. Every one of those is a `new-term` queue entry
that never happens. This is the single largest reducer of runtime interruption
and it is not optional.

Likewise: register the sources before ingesting them, author `outline.yaml` from
the textbook's table of contents in the same pass, and seed `symbols.yaml` from
the field rule document. Each is a queue that then stays empty.

## What "setup complete" means

Setup is complete, and you stop, when all of the following hold. Report against
this list; do not stop early to check in.

- [ ] `make bootstrap` has vendored the pinned toolchain and fonts, shas verified
- [ ] `make check` passes from a clean clone
- [ ] `make rules` has produced `generated/` and the parity of frames against the
      rule documents is asserted by a conformance test
- [ ] Phase 0 spikes executed and their measurements written into `config.yaml`
- [ ] Phase 1 vertical slice compiles a PDF from real ingested material
- [ ] `DECISIONS-TAKEN.md` lists every autonomous choice
- [ ] Anything that hit a hard stop is described, with what you tried
