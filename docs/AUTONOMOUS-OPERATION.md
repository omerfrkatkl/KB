# Autonomous operation protocol

The owner starts Claude Code once, says "start", and does not answer questions during
setup. This document defines how that is possible without the agent guessing.

## The rule

**Never ask. Choose the documented default, record the choice, continue.**

Every decision the setup can encounter falls into exactly one of three classes:

| class | behaviour |
|---|---|
| **Documented default** | Apply it. Append one line to `DECISIONS-TAKEN.md`. Do not ask. |
| **Measurable** | Run the stated procedure, record the number, use it. Do not ask. |
| **Hard stop** | Only three exist (below). Stop, write the reason, leave everything committed and resumable. |

If a decision appears that fits none of these, that is a **defect in this document**,
not a reason to ask. Choose the most conservative option, log it as
`UNDOCUMENTED-DEFAULT`, and continue. The owner reviews those lines afterwards.

Conservative means, in order: preserve information over discarding it; flag over
force-fit; smaller scope over larger; stop a stage over corrupting the store.

## Why this doesn't produce silent garbage

Asking nothing is safe here only because the architecture already separates the two
kinds of uncertainty. Setup decisions are *reversible* — a wrong default changes a
config value or a module boundary, and regenerating fixes it. Content decisions are
*not* reversible, which is why they route to review queues instead. The protocol
removes the first kind of interruption entirely and does nothing to the second.

## The three hard stops

Only these. Everything else is a default or a measurement.

1. **A required credential is absent or rejected** — Claude Code not logged in,
   rclone not configured, Drive OAuth expired. Nothing can proceed and no default
   substitutes for a secret.
2. **A Phase-0 measurement contradicts the plan** — e.g. extraction fidelity falls
   below the stated exit criterion, or throughput cannot meet the configured budget.
   Building on a falsified premise is worse than stopping. Report the measurement.
3. **The store would be corrupted** — a migration that would rewrite existing items,
   or any operation that cannot be rolled back by regeneration.

A queue filling up is *not* a hard stop. Queues are the designed asynchronous channel;
the pipeline continues and the owner works them when convenient.

## Defaults for every open decision

| decision | default without asking |
|---|---|
| A10 board-fidelity fallback | If the WP0.3 board score is below the exit criterion, enable review-gating for board items in config and continue. Do not ask; record it. |
| A11 throughput shortfall | Reduce `max_pages_per_night` to the measured sustainable value and enable weekend catch-up. Do not reduce audit frequency — the audit is the loss defence. |
| Unclassifiable content | `unclassified` queue. Never force-fit. Never drop. |
| Unknown term | Canonicalise as written, queue for ruling, continue. Do not block the batch. |
| Near-duplicate below `auto_confirm` | Queue. Never auto-merge on a guess. |
| Missing figure decision | Review-gate. Figures are rare; a gate costs seconds. |
| Model or CLI version drift | Record the version in provenance and continue. Never pin silently. |
| Any ambiguity in the rule documents | Follow the precedence header (field > Proof Style > Common). If still ambiguous, take the more restrictive reading and log it. |

## Values that are measured, never asked

| value | procedure |
|---|---|
| `resolution_floor_px` | Binarise each Phase-0 capture, take median connected-component height over text regions, set the floor at the 10th percentile of the *legible* set as scored in WP0.3. Write the number to config. |
| `max_pages_per_night` | Run WP0.3 batches while recording wall-clock and rate-limit events; set to 70% of the sustained rate observed over one 5-hour window. |
| `dedup.auto_confirm` / `queue_floor` | Start at the config values. Retune only after the WP2.4 overlap trial, using its labelled pairs. |
| `unnumbered_advances` | Already resolved empirically (false). Re-verify by the parity test; do not re-derive. |

## Phase gates are self-certifying

Each gate is a script that passes or fails on evidence, not a conversation.

- **Phase 0** — `make check` green; parity test green; scorecard produced with all
  columns populated; `resolution_floor_px` and `max_pages_per_night` non-zero.
- **Phase 1** — chapter builds to PDF; zero validation failures outstanding; the
  20-proof pilot scored and its distortion count recorded.
- **Phase 2** — overlap trial merges correctly; zero silent synonym leaks (assert by
  running `relint` and observing no changes).
- **Phase 3** — one lecture week ingested end to end; audit reports resolved or queued.
- **Phase 4** — seven consecutive scheduled runs with no manual intervention.

A gate that fails writes its evidence and stops. It does not ask what to do.

## What still interrupts, honestly

Setup is interruption-free. *Operation* is not, and cannot be: the review queues exist
because the owner ruled that unclassifiable content must never be force-fitted, and
removing human judgment from that loop means silently mis-typing mathematics. What is
achievable is making the queues rare, and the largest single reducer is pre-seeding
the lexicon: the four rule documents already contain roughly 150 canonical/banned term
pairs, which become rulings that never need to be asked. That is a Phase-1 task
(WP1.4A), not a runtime one.

Expect: dense queue activity in a field's first two weeks, decaying to minutes per
week as the lexicon converges.
