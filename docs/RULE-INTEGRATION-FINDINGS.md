# Rule-Document Integration — findings from compiling Proof Style into frames v1
Executed 2026-07-28. Same 14 items, same lecture, same template.
Compare: harmonic-functions-slice.pdf (frames v0) vs harmonic-slice-rulecompliant.pdf (frames v1).

## Rulings implemented
A16 by-ref -> name if the target has one, else its full statement. Zero citations by number
    (audited: 0 occurrences of @thm-/@def-/@prop- in the generated source).
A17 Proof Style §3.2 six-way transition selection, computed from `justification.kind`.
A18 zero occurrences of "we"; structural openings are imperative
    ("Consider n cases.", "Proceed by induction on $n$.", "Prove the contrapositive.",
    "Construct [object] explicitly."). The biconditional opener was DELETED rather than
    rephrased -- the $(=>)$/$(arrow.l.double)$ markers already carry the structure.
A19 compiler-verified: `<=` renders as the relation ≤ (U+2264), so Proof Style §4.5 was
    defective; Common §20's `==>`/`<==` was valid but long (⟹/⟸). Now `=>` / `arrow.l.double`
    (⇒/⇐, U+21D2/U+21D0).
A20 justification presence computed at build time from store membership.

## A20 in action — the visible consequence
Every "by the fact that the Cauchy-Riemann equations hold" justification DISAPPEARED,
because the Cauchy-Riemann equations are not yet an item in this document. Per Proof Style §2
this is correct: justify only what the reader can verify inside the book. The steps now read
"Then $u_x = v_y$ and $u_y = -v_x$ in $D$." with no why. When the Cauchy-Riemann theorem is
ingested from Brown & Churchill, every one of these justifications reappears automatically,
in named form ("by the Cauchy-Riemann Theorem"), with no re-extraction.

Surviving justifications are exactly the in-document ones: the harmonic-conjugate definition,
and the two theorem citations rendered by content.

## Two frame bugs found by rendering (fixed)
1. TAUTOLOGICAL CITATION. Citing an unnamed theorem by its *conclusion* produced
   "Therefore $u$ and $v$ are harmonic in $D$, by the fact that $u$ and $v$ are harmonic in $D$."
   Fix: "content of the fact" (§2.1) = the FULL statement, composed as
   "if [hypotheses], then [conclusion]". Now reads: "...by the fact that if $f(z) = u + i v$ is
   analytic in a domain $D$, then $u$ and $v$ are harmonic in $D$."
   RESIDUAL: composed statements are verbose. A `citation_form` slot (the result as one
   subordinate clause, e.g. "the real and imaginary parts of an analytic function are harmonic")
   would read far better. Extractor-produced, review-confirmed. -> [A21]
2. MISSING PROOF OPENING. §4.1 requires a direct proof to open with Let/Assume; the first step
   was opening with "Then". Fix: the opening is DERIVED deterministically from the parent
   statement's hypotheses ("Assume that [hypotheses]."). No new data needed.

## Two content-level violations the regex engine must catch (evidence for its role)
Both lived in LLM-transcribed slot content, not in frames:
- "harmonic conjugate of $u$ on $D$", "constant on $D$"  -> CA §6 requires "in $D$"
- "..., so $u$ is not a harmonic conjugate of $v$"        -> Common §14 forbids "so"
These are precisely the class your engine should check at the per-item validation stage,
before storage. Frames cannot catch them; they are inside the slots.

## Rule-document defect list (for your editing pass)
- Common §15.2 deleted per A17.
- Proof Style §3.2's "we" ban vs §4.3/4.4/4.5/4.7 mandated "We ..." openings: resolved by A18
  (openings rewritten imperative).
- Proof Style §4.5 arrow pair corrected per A19.
- Proof Style §3.2 ("pure algebra -> Then") vs §6.2/§7.x patterns ("Therefore ..., by direct
  computation"): genuine internal tension. frames v1 follows §3.2 (the general rule) and renders
  "Then [claim], by direct computation." -> [A22]
- CA §5.4 "NEVER write 'domain' alone" / "ALWAYS write 'domain' to mean a connected open set"
  is not implementable as written; needs restating.
- ODE override header misquotes Common §6 (claims Common says "IF single-variable THEN $f'(x)$";
  Common §6 says ALWAYS prime). The override is a no-op. Housekeeping.
- Common §15.4 / Proof Style §3.4 and Common §15.5 / Proof Style §3.3 are duplicated with
  divergent prohibition lists. Keep one copy each (recommend: Proof Style owns proof rules).
