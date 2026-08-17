# Capture corpus analysis — Linear Algebra and Abstract Algebra board photographs
Performed 2026-07-31 against Google Drive metadata. 200 files sampled
(100 per subject; both folders hold more — the listing paginates).

## What was analysed, and what was not

ANALYSED: filenames, upload timestamps, file sizes, sequence numbers — everything
Drive exposes as metadata. This is enough to test the session-grouping design, the
volume assumption, and the batching parameters, and it turned up one design defect.

NOT ANALYSED: the images themselves. Reading them through this interface means
base64-encoding each one into the conversation at roughly 50,000 tokens apiece;
200 photographs is not feasible, and a handful sampled by eye would produce exactly
the kind of unverifiable claim that had to be withdrawn from the earlier "vertical
slice". Content, legibility, and board-quad behaviour are WP0.3 measurements, to be
made by the pipeline on the desktop, under the schemas, with the coverage audit.

## Corpus shape

| | Linear Algebra | Abstract Algebra |
|---|---|---|
| lecture days | Tuesday, Thursday | Monday, Wednesday |
| window sampled | 2026-03-03 .. 04-09 (37d) | 2026-02-16 .. 04-06 (49d) |
| lectures | 11 | 11 |
| photos per lecture | 7 / 9 / 21 (min/median/max) | 1 / 8 / 17 |
| rate | ~19 per week | ~14 per week |

Filenames follow `MM.DD.YYYY~NN.jpeg` without exception across all 200 files. The
date is the lecture date; `NN` is the capture index within that lecture.

## FINDING 1 — session grouping by timestamp is broken (defect)

Plan §I-6.5 groups board photographs into sessions by "EXIF-time gaps greater than
`session_gap_minutes`", defaulting to 45. Against this corpus that rule fails:

| upload batch | files | lectures | span |
|---|---|---|---|
| 2026-03-20 | 23 | **2** | 20 min |
| 2026-03-11 | 22 | **2** | 3 min |
| 2026-04-07 | 13 | **2** | 5 min |
| 2026-04-07 (LA) | 46 | **5** | **15 min** |

Four of fifteen upload batches contain more than one lecture. The worst case merges
five distinct lectures — three weeks of Linear Algebra — into a single 15-minute
window. Upload lag ranges from 0 to 14 days, so upload order does not even preserve
lecture order.

The cause: Drive's `modifiedTime` is when the file was *uploaded*, not when the
photograph was *taken*. Any grouping derived from it describes the owner's upload
habits, not the lecture structure.

What this costs, concretely: the open-item set from one lecture would be offered as
continuation targets for a lecture three weeks later; a "Last Time" review board
would be matched against the wrong prior session; and unrelated material would share
an extraction call, degrading the context that §7.3 continuation depends on.

Ranked signals, best first:
1. **A dated subfolder per lecture** (`Lecture-Boards/2026-03-05/`) — structural,
   cannot be inferred wrongly, survives any metadata loss. This is the same move
   that made `kind` a folder rather than a guess (A23).
2. **EXIF `DateTimeOriginal` read from the file bytes** — true capture time when
   present. Whether it survives the phone -> Drive -> rclone path is B10, still
   unverified; Drive's own metadata does not expose it.
3. **The filename date** — verified correct on 100% of 200 files here. Note the
   standing instruction not to parse filenames was given about *screenshots*, which
   come from several devices with no shared convention. Board photographs evidently
   come from one workflow with a rigid one.
4. **Upload timestamp** — demonstrably wrong; usable only as a last resort, and only
   with a flag raised.

Recommended: implement 2 -> 3 -> 4 with explicit precedence and a warning whenever
the fallback is reached, and adopt 1 going forward if the owner prefers grouping
that cannot silently break. -> **[A26]**

## FINDING 2 — the volume assumption is conservative (B3)

| | photos/week |
|---|---|
| observed, two subjects | ~33 sampled, ~38 corrected for undersampling |
| extrapolated to four subjects | ~76 |
| planning figure in the spec | 200 |

The spec's worst case is about 2.6x the rate four subjects at this cadence would
actually produce. B3 (whether the volume fits the Pro subscription's limits) is
therefore less pressing than assumed, though it still needs the WP0.4 measurement,
because cost per photograph — not photograph count — is the unknown.

Bursts matter more than the average: the 2026-04-07 upload delivered 46 photographs
at once, roughly 70-90 board crops, 12-15 extraction batches. The nightly budget must
absorb a burst of that size, or spread it across nights without losing session
coherence.

## FINDING 3 — batching parameters are about right

Implied photos per lecture: median 9, maximum 21. At `batching.board_crops = 6`, and
1-2 crops per photograph, a median lecture is 2-3 extraction calls and the largest is
5-7. Small enough that a whole lecture's context stays coherent, large enough not to
waste calls. No change recommended.

## FINDING 4 — two anomalies worth a glance

- `Abstract-Algebra/02.16.2026~01` is a lone photograph for that date. Either a test
  shot or a lecture captured once and abandoned.
- Sequence numbers exceed the sampled count in three lectures (LA 03.03 shows 21,
  AA 03.02 shows 13), confirming the listing truncation rather than missing files.

## Recommended Phase-0 fixtures, chosen from this corpus

- **LA 2026-03-03** (21 photographs) — the largest session; stresses batching,
  continuation across many captures, and within-session duplication.
- **LA 2026-04-07 upload batch** (46 files, 5 lectures) — the exact case that breaks
  timestamp grouping. Whatever grouping rule is implemented must split this correctly.
- **AA 2026-03-23** (17 photographs) — second largest, different lecturer and subject;
  guards against tuning to one hand.
- **AA 2026-03-11 and 2026-03-16** — consecutive lectures uploaded in one batch;
  the minimal reproduction of Finding 1.
