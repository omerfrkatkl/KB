# Frame/emitter demonstration — SYNTHETIC INPUT

**Correction, 2026-07-31.** An earlier version of this file claimed these items were
extracted from ten board photographs of a 2026-05-03 lecture, and carried a
photo-by-photo coverage table. That was false and has been removed. The board
photographs are Linear Algebra (T-invariant and T-cyclic subspaces, the
Cayley–Hamilton theorem, Friedberg §5.4). The items below are Complex Analysis and
were **written by hand as a demonstration**, not extracted from any source.

## What this demonstration does and does not establish

ESTABLISHED — by compiling and inspecting real output:
- The frame grammar renders a full document: definitions in both noun and predicate
  form, theorem-class statements, five proof methods, cross-item citations.
- `frames.py` obeys the rule documents on generated text. Audited mechanically on
  the output: zero occurrences of "we", zero forbidden connectives, zero citations
  by number, correct ⇒/⇐ arrows.
- A20 (build-time justification membership) behaves as specified: justifications
  for facts absent from the document are suppressed and reappear when those facts
  are added.
- The emitter, `numbering_sim.py`, and the star-patched template compose into a
  compiling PDF with correct numbering and resolvable references.

NOT ESTABLISHED — these require real material and are still open:
- **B7** — whether the proof step-grammar expresses real proofs without distortion.
  Untested. The `iff-pair` method and the by-fact/pending-ref routing rule were
  invented for this demonstration, not derived from observed material.
- **B12** — continuation across captures, review-repeat collapse, and
  worked-demonstration exclusion. No evidence exists.
- **B1** — board extraction fidelity. No extraction was performed.

## Artifacts

`tests/fixtures/synthetic/` — the hand-written item set, emitter, and generated
Typst. Useful as a golden-output regression fixture for the renderer. It is not
evidence about extraction, and must never be cited as such.
`reference/synthetic-slice-rulecompliant.pdf` — the compiled result.
