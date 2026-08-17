# Findings

What was learned by examining real material — board photographs, the capture
corpus, the rule documents, and the real toolchain. This supersedes seven
separate documents (`BOARD-CONTENT-ANALYSIS`, `BOARD-EXTRACTION-FINDINGS`,
`CAPTURE-CORPUS-ANALYSIS`, `RULE-INTEGRATION-FINDINGS`, `S3-RESULTS`,
`SLICE-FINDINGS`, `SETUP-REPORT`), which are preserved in git history at commit
`342ac30`.

Everything here is input to work that is still pending. It is not a historical
archive: findings whose consequence was already written into
`docs/implementation-plan.md` or `DECISIONS-TAKEN.md` were dropped, and what
remains is what a work package, a test, or a measurement still needs. Each entry
carries the date it was established and the document it came from.

---

## Capture and resolution

**The resolution floor is calibrated against wide shots, not close ones.** Wide
framing with dense content is where subscripts die; a floor set from close
captures does not bound the failure (2026-07-31, board-content analysis).

The failure classes to measure it against, all observed:

- superscripted indices inside subscripted terms — a doubly-indexed family in a
  finite-sum expression was at the edge of legibility for a human reader;
- plus-or-minus versus minus-or-plus in a quadratic-formula step, which silently
  swaps two eigenvalues when read wrong;
- red chalk on a green board at small size — the worst contrast in the set, and
  the first thing lost at low resolution;
- motion blur, which made a subscripted ideal generator ambiguous.

**One image in twenty sits at the edge.** A soft-focus frame was still readable
but is the frame where a subscript would be lost first. That sets the practical
floor: the gate must catch that class rather than pass it through silently
(2026-08-01, board-photograph analysis).

**Human legibility is not the constraint.** Every mathematical symbol in
nineteen of twenty images was readable, including the cases expected to fail:
subscripts, superscripts, matrix entries in 3×3 determinants, integral bounds,
and quotient notation. See the standing caution below for what this does and does
not settle about B1 (2026-08-01, board-photograph analysis).

## Board content and taxonomy

**Board items are labelled**, contradicting the headless-prose worry: Defn,
Definition, Proposition, Prop, Theorem, Thm, Example, Exercise, Remark, Recall,
Note, Claim, Pf. Unlabelled prose is a *textbook* problem, not a board problem
(2026-07-31, board-content analysis).

**Taxonomy matching must go through an alias table, never exact strings.** The
abbreviations are inconsistent within a single lecturer, let alone across three:
Defn/Definition, Prop/Proposition, Thm/Theorem, Pf/Proof, ex/Example
(2026-07-31, board-content analysis).

**Photograph-to-photograph overlap is dense.** At least eight of twenty shared
substantial content with another in the set: the same example photographed twice
with the second adding a computation below and repeating the board above
verbatim; a board appearing as the subject of one photograph and as edge bleed in
the next; a four-photograph chain through one topic, each showing the previous
board as a partial strip. Consequences: item-level deduplication carries real
load from the first day, and a proof interrupted by a board change is usually
recoverable because the overlap re-photographs the earlier half (2026-07-31,
board-content analysis).

**The sliding-board pairs are WP3.2's regression fixture.** Two pairs show the
same physical board photographed twice at different scroll positions — the
characteristic-polynomial board as the main subject of one capture and as the
upper band of the next, with the eigenvalue computation continuing below; a third
pair does the same across the T-invariant example and the SPOILER board. Position
is meaningless; content matching is the only viable rule (2026-08-01,
board-photograph analysis).

**No figures appeared** in twenty photographs of two algebra courses. Boxed and
arrowed annotations are layout, not figures. This sample gives no evidence about
figure handling in either direction; expect that evidence from geometry or
analysis (2026-07-31, board-content analysis).

**Open — standing conventions.** A board carried `Throughout the rest, R is a
commutative ring with 1_R ≠ 0_R`. It is excluded as narrative today, but it is
arguably `context` on every item that follows. Unresolved; watch it in WP0.3
(2026-08-01, board-photograph analysis).

## Citations

**An explicit external identifier can never resolve to a store item.**
`Example 3, page 372` belongs in `pending_refs` and, on review, becomes a
provenance note rather than a citation (2026-08-01, board-photograph analysis).

## Notation

**The source is not self-consistent, and the extractor must normalise rather
than preserve.** Within one course, one lecturer, sometimes one proof:

- `I, J ⊆ R` and `I, J ⊂ R` for the same relation, on two boards of one proof;
- `I·J` and `IJ` for the same product, three lines apart;
- `(n)+(m)=(d)` on one board and `(m)+(n)=(d)` on the next.

This is the drift the canonical lexicon and symbol registry exist to remove,
observed rather than hypothesised. "Preserve the source's notation" is the wrong
instruction; the rule documents are what it normalises *to* (2026-08-01,
board-photograph analysis).

## Session grouping and volume

**Upload timestamps do not carry session identity.** Four of fifteen upload
batches held more than one lecture; the worst merged five distinct lectures —
three weeks of Linear Algebra — into a single fifteen-minute window. Upload lag
ranges from 0 to 14 days, so upload order does not even preserve lecture order.
The cause is that Drive's `modifiedTime` is when the file was uploaded, not when
the photograph was taken. This is the defect the `groups.py` precedence exists to
prevent, and `tests/test_ingest.py::test_five_lectures_in_one_upload_do_not_merge`
is its regression test (2026-07-31, capture-corpus analysis).

**Filename dates were correct on 200 of 200 board photographs** (`MM.DD.YYYY~NN.jpeg`
without exception). The standing rule against parsing filenames was given about
*screenshots*, which come from several devices with no shared convention; board
photographs come from one workflow with a rigid one. This is why a filename date
outranks the file timestamp in the precedence (2026-07-31, capture-corpus
analysis).

**Volume is about 2.6× below the planning figure.** Roughly 38 photographs per
week across two subjects, extrapolating to ~76 for four, against the
specification's 200/week worst case. Bursts matter more than the average: one
upload delivered 46 photographs at once — roughly 70–90 board crops and 12–15
extraction batches. The nightly budget must absorb a burst of that size, or
spread it across nights without losing session coherence. Input to WP0.4
(2026-07-31, capture-corpus analysis).

**Batching parameters are adequate as configured.** Median 9 photographs per
lecture, maximum 21. At `batching.board_crops = 6` and 1–2 crops per photograph,
a median lecture is 2–3 extraction calls and the largest 5–7 — coherent context,
no wasted calls. No change indicated (2026-07-31, capture-corpus analysis).

**WP0.3's golden fixtures, chosen from the real corpus** (2026-07-31,
capture-corpus analysis):

- **LA 2026-03-03**, 21 photographs — the largest session; stresses batching,
  continuation across many captures, and within-session duplication.
- **The LA 2026-04-07 upload batch**, 46 files across 5 lectures — the exact case
  that breaks timestamp grouping. Any grouping rule must split it correctly.
- **AA 2026-03-23**, 17 photographs — second largest, different lecturer and
  subject; guards against tuning to one hand.
- **AA 2026-03-11 and 2026-03-16** — consecutive lectures uploaded in one batch;
  the minimal reproduction of the grouping defect.

## Toolchain and numbering

**B5 — unnumbered math environments do not advance the shared counter.**
`UNNUMBERED_ADVANCES = False` in `build/numbering_sim.py`. Verified twice against
typst 0.15.1, by probe and by the full parity test: unnumbered environments carry
no label, `@`-refs resolve, and the counter resets at level-1 headings
(2026-07-20, S3 results).

**The exam star cannot travel as a parameter.** The figure show-rule boundary has
no parameter channel, so the flag travels via a `state("math-env-star")` set by
each item and read at the figure's location. This is why `star.patch` is a
152-line unified diff against an estimate of ~10 lines; anything that touches the
star path has to keep the state channel (2026-07-20, S3 results).

## What is not evidence

**No extraction has ever been performed by this system.** Every extraction-side
claim in this repository is unverified.

**`tests/fixtures/synthetic/` is a renderer regression fixture and never evidence
about extraction quality.** An earlier document recorded those items as an
extraction from ten board photographs of a 2026-05-03 lecture, with a
photo-by-photo coverage table. That was false: the items are Complex Analysis and
were written by hand as a demonstration, and the board photographs are Linear
Algebra. Do not cite the fixture as evidence about extraction (2026-07-31, slice
findings).

What that demonstration *does* establish, by compiling and inspecting real
output: the frame grammar renders a full document — definitions in noun and
predicate form, theorem-class statements, five proof methods, cross-item
citations; the generated text obeys the rule documents under mechanical audit
(zero "we", zero forbidden connectives, zero citations by number, correct ⇒/⇐);
A20's build-time justification membership behaves as specified, suppressing
justifications for absent facts and restoring them when those facts are added;
and the emitter, `numbering_sim.py`, and the star-patched template compose into a
compiling PDF with correct numbering and resolvable references.

What it does not establish: **B7** — whether the proof step-grammar expresses real
proofs without distortion — is untested, and the `iff-pair` method and the
by-fact/pending-ref routing rule were invented for that demonstration rather than
derived from observed material; **B12** — continuation across captures,
review-repeat collapse, worked-demonstration exclusion — has no evidence at all
(2026-07-31, slice findings).

**Legibility was assessed by a person reading images in a chat interface, not by
the pipeline running its schemas with validation and audit.** It bounds
legibility and segmentation difficulty; it does not measure what the runtime
model will do under the prompt pack (2026-07-31, board-content analysis).
</content>
</invoke>
