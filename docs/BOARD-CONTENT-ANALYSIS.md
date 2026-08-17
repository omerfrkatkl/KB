# Board content analysis — 20 photographs read directly
Performed 2026-07-31. Ten Abstract Algebra (ring theory: direct products, ideals,
comaximality) and ten Linear Algebra (§5.4 invariant subspaces and Cayley-Hamilton;
§6.3-6.5 adjoints, unitary and orthogonal operators). At least three different
lecturers appear across the set.

This is the first analysis in the project grounded in real captured material rather
than metadata or assumption.

## FINDING 1 — foreign-subject boards (breaks a stated assumption)

One photograph shows two board columns: the left carries the ring-theory lecture
(intersection of a family of ideals, the First Isomorphism Theorem, the sum of two
ideals), and the right carries **differential geometry** — regular curves, unit
tangent vectors, a constant angle theta, the ratio of torsion to curvature. It is a
shared lecture hall and a previous class's boards were never erased.

The plan (I-6.3) instructs the extractor to "ignore content clipped by the edge of
the image." That rule does not reach this case: the differential-geometry board is
fully visible and uncropped. It simply belongs to someone else's lecture. Board-quad
detection would crop it cleanly and hand it to extraction as a legitimate region.

Left unhandled the outcomes are all bad: curve-theory content extracted into the
Abstract Algebra book, or a coverage audit reporting it as a gap the extractor
wrongly skipped, forever.

FIX: a new exclusion class `foreign-subject` — content that is topically disjoint
from the field being extracted. This is decidable semantically (the extractor is told
the field and carries its lexicon) where it is not decidable geometrically. Also
added to the audit prompt, so the auditor validates rather than re-reports it.

## FINDING 2 — consecutive photographs overlap heavily (good news)

At least eight of the twenty share substantial content with another in the set:

- Two photographs of the same T-invariant-subspace example, the second adding the
  eigenspace computation below while repeating the characteristic-polynomial board
  above verbatim.
- Two of the T-invariant claim board, the second adding the "SPOILER" panel.
- The direct-products board appears once as the subject of one photograph and again
  as edge bleed on the left of the next.
- A four-photograph chain through the comaximal-ideals material, each showing the
  previous board as a partial strip.

This is the redundancy the continuation and duplicate machinery was designed for,
and it is far denser than assumed. Two consequences: item-level deduplication will
carry real load from the first day, and a proof interrupted by a board change is
usually recoverable because the overlap re-photographs the earlier half.

## FINDING 3 — board content is *labeled*, contradicting the headless worry

Nearly every item on these boards carries an explicit label: Defn, Definition,
Proposition, Prop, Theorem, Thm, Example, Exercise, Remark, Recall, Note, Claim, Pf.
The unlabelled-prose problem that drove the segmentation rules is a *textbook*
problem, not a board problem.

But the abbreviations are inconsistent within a single lecturer, let alone across
three. The taxonomy needs an alias table (Defn/Definition, Prop/Proposition,
Thm/Theorem, Pf/Proof, ex/Example) rather than exact-string matching.

## FINDING 4 — exercise statements assert real facts

One board reads: "Exercise: Show that a T-cyclic subspace is T-invariant. Moreover,
show that it is the smallest T-invariant subspace containing x."

Two true, useful mathematical facts, in imperative framing. A9 excludes exercises
entirely; the no-information-loss requirement wants the facts. The A14 precedent
already resolves the identical tension for proofs inside exercise apparatus: the
content is in scope, the question framing is not.

RULING (by precedent, flagged for veto): the *statements* are extracted as
propositions with `proofs: []`; the imperative framing is dropped. "Show that a
T-cyclic subspace is T-invariant" becomes a proposition whose conclusion is that a
T-cyclic subspace is T-invariant. This is A14 applied to statements rather than
proofs, and inventing a different answer for the parallel case would be incoherent.

## FINDING 5 — a real counterexample, validating the schema

One board carries: "Surprise: Prop 1 does not hold, because T does not have any
eigenvectors" — for the multiplication operator on the span of the exponential basis
of continuous complex-valued functions on the circle. That is precisely
`counterexample` with `establishes: hypothesis-necessary`: it shows finite
dimensionality cannot be dropped from the preceding proposition. The type introduced
speculatively under A12 has now been seen in the wild.

The same board also carries "A typo in our textbook" with the correct integral. That
is commentary about a source, not a mathematical fact about the subject — `narrative`.

## FINDING 6 — coloured chalk is semantically loaded, and the plan ignores it

Four colours appear beyond white: blue for elaboration (naming a set-builder
expression "a plane"), orange for a summary table of the subspaces found, red for
emphasis on the decisive quantity (circling "multiplicity one" and the bound it
forces), salmon for corrections and cross-references to a previous theorem.

No rule in the system mentions colour. Two honest positions: ignore it (simple,
loses the lecturer's own signal about what matters), or treat red/circled emphasis
as a refinement of exam-relevance. I have not designed for it — this is recorded as
an observation, with a recommendation to ignore colour in v1 and revisit only if the
exam star proves too coarse. Note that red on green is also the *worst* contrast in
the set and the most likely to be lost at low resolution.

## FINDING 7 — transcription risks, concretely

Legibility is good overall; I transcribed nearly everything with confidence. The
specific failures cluster:

- **Superscripted indices inside subscripted terms** — a doubly-indexed family in
  a finite-sum expression was at the edge of legibility even for me.
- **Plus-or-minus versus minus-or-plus** in the quadratic-formula step of an
  eigenvalue computation. Getting this backwards silently swaps two eigenvalues.
- **Red chalk on green board** at small size.
- **One motion-blurred photograph**, where a subscripted ideal generated by an
  element was ambiguous.
- **In-line corrections**: a caret inserting "commutative" above a line, and a
  struck-through term replaced beside it. The extractor must read the corrected
  text, not the original.

Wide framing with dense content is where subscripts die. The resolution floor should
be calibrated against the *wide* shots, not the close ones.

## FINDING 8 — no figures in this sample

Zero diagrams, plots, or geometric drawings across twenty photographs of two
algebra courses. The boxed-and-arrowed annotations are layout, not figures. This
sample gives no evidence about figure handling either way; expect that evidence from
geometry or analysis courses instead.

## What this does not tell us

The extraction was performed by me reading images in a chat interface, not by the
pipeline through its schemas with validation and audit. It bounds legibility and
segmentation difficulty; it does not measure what the runtime model will do under
the prompt pack. B1 is *informed*, not resolved.
