# Rule Document Edits — 2026-07-29

Five files edited. Every change is one of: a contradiction resolved, a redundancy
collapsed to a single owner, a gap filled, or a defect corrected. Rulings A16–A22
are now written into the documents rather than living only in the plan.

## Structural change — the fix that prevents recurrence

The documents had no precedence rule and no ownership rule, which is why the same
rule appeared in two files with different content. Both are now stated in the
Common.txt header and pointed to from the other three:

    PRECEDENCE   field file  >  Proof_Style.txt  >  Common.txt
    OWNERSHIP    Common      — notation, universal language, STATEMENT forms
                 Proof Style — everything inside a proof
                 field files — field notation, terminology, theorem names

A rule is stated once, in its owning file. Elsewhere it appears only as a pointer.
Deleted sections are kept as [MOVED] / [MERGED] stubs so section numbers stay stable.

## Contradictions resolved

1. Transitions. Common 15.2 mandated "Therefore" for every intermediate step;
   Proof Style 3.2 mandates a six-way context-dependent choice. Common 15.2 withdrawn
   (A17); Proof Style 3.2 is the owner.
2. Biconditional arrows. Common 20 used `$(==>)$/$(<==)$`, Proof Style 4.5 used
   `$(=>)$/$(<=)$` — and `$<=$` compiles to the relation ≤ (U+2264), not an arrow.
   Verified against typst 0.15.1. Now `$(=>)$` / `$(arrow.l.double)$` (⇒/⇐), stated
   once in Proof Style 4.5 with the compiler evidence recorded (A19).
3. The "we" ban. Proof Style 3.2 forbade phrases beginning with "we" while 4.3–4.7
   mandated "We consider…", "We proceed…", "We show…", "We construct…". The token is
   now banned outright in Common 14 and Proof Style 3.2, and every structural opening
   is imperative: "Consider [n] cases.", "Proceed by induction on $n$.",
   "Prove the contrapositive.", "Construct [object] explicitly." (A18)
4. "i.e." Common 18 forbids it; Proof Style 4.4 mandated it for the inductive
   hypothesis and 6.5 used it. Both now use "that is".
5. Computation steps. Proof Style 3.2 assigns "Then" to pure algebra, but every
   pattern in 6.x and 7.x wrote "Therefore …, by direct computation". All nine
   patterns corrected to "Then" (A22).
6. Derivative notation. The ODE OVERRIDE block claimed to override a Common rule that
   does not exist ("IF single-variable, THEN $f'(x)$") and then mandated exactly what
   Common already mandates. Replaced with an accurate RELATION note; the Leibniz ban,
   which was only in the ODE file, is now stated universally in Common 6.

## Redundancies collapsed

7. Referencing results — Common 15.4 and Proof Style 3.4 duplicated with divergent
   prohibition lists. Proof Style 3.4 owns; it also now permits exactly one use of
   "above" ("by the claim above") and forbids equation- and section-number citation.
8. Proof closing — Common 15.5 and Proof Style 3.3 duplicated, each pointing at the
   other. Proof Style 3.3 owns, including both template QED behaviors.
9. Let / Assume / Suppose — Common 15.1 and 15.3 and Proof Style 3.1 overlapped.
   Common 15.1 now states the three word meanings once; Proof Style 4 states which
   word opens which proof type. Common 15.3 merged into 15.1.
10. Proof structure — Common 20 duplicated Proof Style 4.3, 4.5, 4.8 and 3.6.
    Proof Style 4 owns; case labels are bold `*Case 1:*` in the one surviving copy.
11. Theorem names — Complex Analysis had two lists (Section 9 with 11 names,
    Section 18 with 16). Section 18 is now the single authoritative list.

## Defects corrected

12. Complex Analysis 5.4 was not implementable: "NEVER write 'domain' alone" followed
    by "ALWAYS write 'domain' to mean a connected open set". Rewritten as two named
    concepts with one rule each.
13. Complex Analysis 6 forbade $u_(x x) + u_(y y) = 0$ outright, while Proof Style 6.2
    required writing it to show the computation. Now separated: $nabla^2 u = 0$ names
    the equation, the subscript form shows the computation.
14. Proof Style 6.2 closed with two "Hence" sentences in one proof, violating 3.3, and
    wrote "harmonic on $D$" against Complex Analysis 6. Both fixed.
15. Proof Style 7.1 justified the characteristic equation with "by the fact that
    $y = e^(r t)$ is assumed" — circular. Split into an assumption and a computation.
16. Proof Style 3.5 stated punctuation goes after the closing delimiter, then gave an
    example with it inside. Now split by math type: inside for display, outside for
    inline.
17. Common 19 wrote both display and inline math as `$...$`, making the rule
    unreadable. Typst distinguishes them by whitespace inside the delimiters; stated.
18. Common 1.1 listed environments that do not exist in the template (`#rem`).
    Replaced with the ten environments the knowledge base actually uses.
19. Proof Style 3.2's own examples violated the rules: unmarked math (`L`, `f(t)`,
    `R`) and a lowercase "therefore" as a mid-sentence connective. Corrected.
20. Proof Style 5.3 and 5.4 concluded with "Then"/"Therefore" where 3.3 requires
    "Hence" as the final sentence. Corrected.

## Gaps filled

21. STATEMENT FORMS — the largest gap. The documents specified proof prose in detail
    and said almost nothing about how definitions and theorem statements are phrased,
    so the renderer had been running on frames with no rule-document backing. New
    Common Section 21 specifies: definition noun form with article (including the
    no-article case for possessive and proper-name terms), definition predicate form,
    the context prefix, theorem-class statement form with hypothesis joining, the
    citation form (21.3), and counterexample admission and phrasing (21.4).
22. Citation form — Proof Style 2.1 now cites unnamed in-document results by their
    citation form and explicitly forbids the composed "by the fact that if …, then …"
    fallback (A16, A21).
23. Justification membership — Proof Style 2 said "appears earlier in the document" in
    one branch and "does not appear anywhere" in the other, leaving forward references
    undefined. Now membership-based and position-independent, with the evaluation-time
    rule stated: membership is determined at build time, so a proof gains
    justifications as the document grows (A20).
24. Proof Style 2 said "write the justification on its first use", which contradicted
    the sub-rule that omits only on an immediately preceding identical justification.
    Clarified: justify at every use except that one case.

## template.typ

The exam-star patch (A1) is applied — `star: false` threaded through `math-item`,
`math-item-unnumbered`, and all three renderers via a `state("math-env-star")` channel,
since the figure show-rule boundary has no parameter channel. Behavior is unchanged when
the flag is unset. `star.patch` is included so the diff against your original is explicit.
The 2026-05-03 lecture recompiles against the patched template with no errors.

## Not changed, deliberately

- Unused environments (`#exer`, `#prob`, `#que`, `#solution`, `#note`, `#num-eq`) remain
  in template.typ per A9. Exclusion is enforced by the taxonomy and the emitter
  allowlist, which is deterministic; deleting template code adds no enforcement.
- Every ALWAYS/NEVER rule that was already correct and singly-owned is untouched.

---

# Rule Document Edits — 2026-08-11

Three scoped bans, three different treatments. All three were found by the same
survey: the compiler represents an *unconditional* pair and nothing else, so a
ban the document scopes in prose compiles to a ban broader than the document
states, and the substitution fires where the document says it must not.

## `line integral → contour integral` (CA §8) — judgment: keep enforced

    ALWAYS use "contour integral" — NEVER "line integral"
    when referring to integration in the complex plane.

**No change made to the rule document or to the code.** The qualifier reads as a
restriction but is not one: "when referring to integration in the complex plane"
describes the default context of a Complex Analysis document rather than
carving out a subset of it. Every contour integral in this corpus is an
integration in the complex plane, so the qualifier excludes nothing and the pair
is safe to substitute unconditionally.

Contrast with the two below, where the qualifier genuinely names a subset: a
neighborhood of infinity is not a punctured disk, and a three-dimensional system
does have a phase space. The test is whether the excluded case can actually
arise in this field's text, not whether a qualifier is present.

> **Correction, 2026-08-11 (same day).** The judgment above is wrong and is
> withdrawn. The qualifier *does* narrow the ban: real line integrals appear in
> this very subject, in the Green's theorem step of the Cauchy–Goursat proof,
> where "line integral" is the correct term and rewriting it to "contour
> integral" would be an error. The pair was briefly added to
> `rules/enforcement-allowlist.yaml` to honour the ruling above and has been
> removed; the fail-closed rule now demotes it on its qualifier.
>
> Demotion defers the rule to a context-aware ruling in the review queue. It
> does not lose it.
>
> Worth recording for the next judgment of this kind: the conflicting-use check
> (below) would **not** have caught this one. `line integral` appears exactly
> once in all of `rules/` — on the line that bans it. The Green's theorem use is
> a fact about the mathematics, not a fact recorded in the documents, so no
> check over the documents can see it. Automation catches contradictions the
> documents state; it cannot catch the ones they omit.

## `degree` (ODE §1.1) — rule-document defect, corrected

The ban was on the bare word. "degree" is correct in its own sense — a
polynomial has a degree, a differential equation has an order — so the pair
rewrote correct text into nonsense ("the degree of a polynomial" → "the order of
the equation of a polynomial"). The document now bans the two phrases that are
actually wrong, and states the correct sense explicitly so the record carries it:

    NEVER write "degree of the equation" or "degree of the
    differential equation" for the order.

The bare pair no longer exists after this edit. The two phrase pairs both parse,
and both are currently demoted by the fail-closed rule on their shared
"for the order" qualifier.

## `phase space → phase plane` (ODE §14.1) — scoped by dimension, demoted

Scoped by a property of the object that no substitution can inspect. §14.1 now
records that "phase space" is correct for dimension three or higher, and the
pair is a proposal ruled on in review.

## The fix that prevents recurrence

Patching pair by pair does not stop the next rule edit from reintroducing the
same defect silently. The compiler now **fails closed**: a prohibition carrying
a qualifier compiles to a proposal unless the pair is listed in the authored
`rules/enforcement-allowlist.yaml`, which is seeded with the four cases whose
qualifiers broaden or describe rather than narrow.

This over-triggers by design. A false demotion costs one queue entry a human
clears in seconds; a false enforcement corrupts the corpus, and
`knowledge-base relint` applies it retroactively to every item already stored.
