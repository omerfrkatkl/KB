# Board photograph analysis — 20 real captures
Performed 2026-08-01. First actual reading of board content by this project.
Supersedes nothing; this is the first evidence that exists on these questions.

## What was in the sample

Not the twenty files requested by name — a different set, and better for it:
three distinct courses appear, not two.

| Course | Material | Images |
|---|---|---|
| Abstract Algebra | ring direct products; ideals; ideal sums, products, intersections; comaximal ideals; principal ideals | 11 |
| Linear Algebra §5.4 | invariant subspaces, T-cyclic subspaces, Cayley–Hamilton setup | 6 |
| Linear Algebra §6.3/§6.5 | adjoint of an operator, unitary and orthogonal operators | 3 |
| **Differential geometry** | regular curves, constant angle, torsion/curvature ratio | **fragment, adjacent board, image 20** |

The §5.4 material overlaps the ten photographs read on 20 July — same lecture
series, earlier in the section. Two sessions of one topic is exactly the
duplicate-and-continuation case the pipeline must handle.

## LEGIBILITY (B1) — pass, with one marginal case

Every mathematical symbol in nineteen of twenty images was readable, including
the cases that were expected to fail: subscripts (`0_R`, `1_R`, `a_i`, `b_i`,
`I_t`), superscripts (`T²(x)`, `t²+t+1`, `A^t`, `e^{int}`), matrix entries in
3×3 determinants, integral bounds, and quotient notation `R/Ker(φ)`.

The one marginal case is a soft-focus frame (ideals examples, `nZ ⊆ Z`,
`I = {p ∈ R[x] | p(0_R) = 0_R}`). Still readable, but it is the frame where a
subscript would be lost first. It sets a practical floor: one image in twenty
sits near the edge, and the resolution gate should catch that class rather than
letting it through silently.

## THE SCHEMA IS INCOMPLETE — B7, with real evidence at last

The step grammar handled every proof's *steps*. The `method` enum did not. Two
structures appear that have no representation, and one setup form is missing.

**1. Double inclusion.** The proof that `IJ = I∩J` for comaximal ideals runs:
`(⊆) always true. (⊇) Since I+J=R, 1_R = a+b for some a∈I, b∈J. So if r∈I∩J,
r = r·1_R = r(a+b) = ra+rb = ar+rb ∈ IJ.` This is set equality by two
inclusions. `iff-pair` is the wrong shape — that renders `(⇒)/(⇐)` for a
biconditional; this needs `(⊆)/(⊇)`, and either direction may be dismissed as
immediate. **New method: `double-inclusion`.**

**2. Criterion checking.** The proof that an arbitrary intersection of ideals is
an ideal verifies the defining properties one at a time: `0_R ∈ ⋂I_t`, then
`a,b ∈ ⋂I_t ⟹ a-b ∈ ⋂I_t`. This is not a linear argument; it is a checklist
against a definition, and the reader must see that the list is complete.
**New method: `verify-criteria`,** carrying the definition being checked and one
block per criterion.

**3. Sufficiency reduction.** A proof opens `It is enough to show that (for n≥2)
dim(W₁) = n(n+1)/2, dim(W₂) = n(n-1)/2`, then derives the goal from those. The
opening replaces the goal with a sufficient condition. No `setup` form expresses
this. **New setup form: `sufficiency`,** rendering `It is enough to show that ⟨…⟩.`

A fourth pattern — set an ansatz, derive constraints, solve — appeared in the
adjoint computation (`Set T*(a+bx) = c+dx`, derive `2c = 10a` and
`2d/3 = 2a + (10/3)b`, conclude `c = 5a, d = 3a+5b`). This fits `construction`
with a `setup`, so no new method, but the extraction prompt should name the
pattern so it is not forced into `direct`.

## THE SOURCE IS NOT SELF-CONSISTENT — the lexicon earns its place

Within one course, one lecturer, sometimes one board:

- `I, J ⊆ R` and `I, J ⊂ R` for the same relation, on two boards of the same proof
- `I·J` and `IJ` for the same product, three lines apart
- `(n)+(m)=(d)` on one board, `(m)+(n)=(d)` on the next

This is precisely the drift the canonical lexicon and symbol registry exist to
remove, observed in the wild rather than hypothesised. It also means the
extractor must not "preserve the source's notation" — it must normalise, and the
rule documents are what it normalises *to*.

## FOUR THINGS THE SPECIFICATION DID NOT ANTICIPATE

**Colour is used, and deliberately.** Orange boxes a summary of results
established earlier; blue annotates a definition inline; red marks a correction
and a multiplicity bound; pink flags the word `correction` beside a fixed line.

*Resolved 2026-08-01 (A27): no special handling in v1.* Coloured content is
extracted exactly as white content and classified by what it says. The
observation stands and the decision is to ignore it — deliberately, because a
colour heuristic would fire on mere emphasis and mis-route content that belongs
in the statement it decorates. The orange summary box, for instance, is caught
correctly by the existing `recall-repeat` rule on content grounds; no colour rule
is needed to reach the same answer. Revisit only if colour-blind extraction is
observed to lose something.

**Boards get corrected in place.** The word `commutative` is inserted above a
line with a caret, changing `If R is a ring` to `If R is a commutative ring`. The
extractor must transcribe the board's *final* state, not its layout order, or it
will emit a statement the lecturer explicitly repaired.

**A different course appears in frame.** One wide capture includes an adjacent
board carrying differential geometry — regular curves, constant angle, the ratio
τ/κ — with no relation to the ring theory being photographed. The existing
"ignore content cut by an image edge" instruction covers it only by luck, since
that board is not clipped, merely irrelevant. The extractor needs a stronger
rule: content belonging to a different subject is `non-content`, regardless of
whether it is fully visible. Without it, differential geometry would have been
filed into Abstract Algebra with board provenance and an exam star.

**Sources get corrected too.** One board reads `A typo in our textbook:
∫e^{int} dt = (1/in)e^{int} + c — missing`, followed by `This typo does not
affect the following`. This is a genuine fact, it is about the source rather
than the mathematics, and it fits no existing type or exclusion class. → **[A28]**

## EXCLUSION BOUNDARIES, OBSERVED

The A14 ruling gets its first real test, twice:

- `Exercise: Show that a T-cyclic subspace is T-invariant. Moreover, show that it
  is the smallest T-invariant subspace containing x.`
- `exercise*: … Show I is NOT principal. In fact I is not even finitely generated.`

Each states two genuine facts inside exercise framing. Per A14 the facts are in
scope and the framing is excluded, so these become proofless propositions —
correct, and the pipeline will later complete them from the textbook. An
extractor that excluded the whole region would silently lose four results.

Correctly excluded: `SPOILER: Why do we need T-inv subspaces?` (motivation),
`Throughout the rest, R is a commutative ring with 1_R ≠ 0_R` (a standing
convention — arguably `context` on every subsequent item rather than narrative,
worth watching), and the worked numerical examples.

## CROSS-REFERENCES, OBSERVED

`by the previous prop`, `Prev Thm`, `In the light of the prev example`, `Recall`,
`§5.4`, `§6.3`, and `Example 3, page 372`. The last is an explicit external
identifier that can never resolve to a store item — it belongs in `pending_refs`
and then, on review, becomes a provenance note rather than a citation. The rest
are exactly the by-fact routing case, confirming the rule adopted on 20 July.

## CONTINUATION AND SLIDING BOARDS, OBSERVED

Two pairs show the same physical board photographed twice at different scroll
positions: the characteristic-polynomial board appears as the main subject in one
capture and as the upper band of the next, with the eigenvalue computation
continuing below. A third pair does the same across the T-invariant example and
the SPOILER board. Position is meaningless, exactly as specified; content
matching is the only viable rule, and these pairs are now the regression fixture
for it.
