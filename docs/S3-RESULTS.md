# S3 Results — executed 2026-07-20 (in-sandbox, real toolchain)

Environment: typst 0.15.1 (pin candidate for tools/VERSIONS); fonts vendored from
official repos (shas in FONT-SHAS.txt: Fira Sans ×5 from google/fonts, FiraMath-Regular
v0.3.4 from firamath releases).

## Facts established
1. **B5 resolved:** unnumbered math-envs do NOT advance the shared counter
   (`UNNUMBERED_ADVANCES = False` in numbering_sim.py). Verified twice: b5 probe and
   the full parity test. Unnumbered envs carry no label; `@`-refs resolve; the counter
   resets at level-1 headings.
2. **Parity test green:** simulation labels == `typst query` labels, element-by-element,
   across 3 chapters, 10 envs (8 numbered), stars, a title, cross-chapter refs, a proof
   with display math, and the full escaping set `\ # $ [ ] { } @ * _ ` < > ~ //`.
3. **Star patch verified** (visual + query): ★ renders in Tier-1/2 badges and before the
   Tier-3 name; unstarred items and all labels/numbering are byte-identically unaffected.

## Deviation from spec worth recording
The plan estimated the star patch at ~10 lines. Actual: a 152-line unified diff.
Reason: the figure show-rule boundary has no parameter channel, so the flag travels via a
`state("math-env-star")` set by each item and read at the figure's location — the original
estimate didn't anticipate that. Behavior when `star` is unset is unchanged (verified).

## Contents
- star.patch            — unified diff against the pristine template.typ
- template-star.typ     — patched template (convenience copy; pristine + patch is canonical)
- numbering_sim.py      — the build-time simulation module (B5 fact encoded)
- gen_torture.py        — emission-plan → torture.typ generator (seed of the real emitter,
                          including the escaping function)
- test_parity.py        — the parity test (compile + typst query + exact comparison)
- torture.typ / torture.pdf — the generated torture document and its build
- FONT-SHAS.txt         — pin values for the bootstrap manifest
