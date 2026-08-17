# Setup report — 2026-08-04

Unattended build of `docs/implementation-plan.md` Part II, from WP0.1 forward, in
a cloud session with **no Google Drive access and no captures**. Run under
`docs/AUTONOMY-PROTOCOL.md`: no questions asked, every choice logged to
`DECISIONS-TAKEN.md`.

**No hard stop was hit.** The build stopped where it was always going to stop —
at the first stage that genuinely requires the owner's material.

---

## Against the completion checklist

| | Item | State |
|---|---|---|
| ✅ | `make bootstrap` has vendored the pinned toolchain and fonts, shas verified | typst 0.15.1 and six fonts fetched, hashed against `template/TOOL-SHAS.txt`, re-verified, idempotent on re-run. A tamper test asserts a changed byte fails rather than warns. |
| ✅ | `make check` passes from a clean clone | 251 tests, verified by cloning to a temporary directory and running `make bootstrap check` there. It did **not** pass as delivered — see "Three day-one breakages" below. |
| ✅ | `make rules` has produced `generated/` and frames parity is asserted by a conformance test | `generated/{lexicon,symbols,validators}` for both fields. `tests/test_frames_conformance.py` reads the mandated strings **out of `rules/` at test time** and asserts frames emits them. |
| ⛔ | Phase 0 spikes executed and their measurements written into `config.yaml` | **Blocked: needs Drive and real captures.** `resolution_floor_px` and `budget.max_pages_per_night` remain 0, which every consumer reads as *unmeasured*. |
| ⛔ | Phase 1 vertical slice compiles a PDF from real ingested material | **Blocked: no material.** The path store → `.typ` → PDF is built and compiles with the real toolchain; what has never gone through it is a real capture. |
| ✅ | `DECISIONS-TAKEN.md` lists every autonomous choice | 15 entries, all `Reversal: cheap`. |
| ✅ | Anything that hit a hard stop is described | None hit. The blocked items above are absent inputs, not hard stops. |

---

## What was built

Everything in Phases 0–4 that does not need source material, in plan order.

| WP | Delivered |
|---|---|
| 0.1 | `config.py` (strict Settings), logging, `bin/pre-commit`, working `make check` |
| 0.2 | ported; the parity test now runs against the pinned typst instead of skipping |
| 1.1 | `models/{item,slots,profile,schemas}.py`, `pipeline/store.py` |
| 1.2 | `route`, `exif`, `registry`, `groups`, `pdfdoc`, `raster`, `resolution`, `sync` |
| 1.3 | `contract`, `runner` (record/replay), `batcher`, `pipeline/accept.py` |
| 1.4 | `pipeline/validate.py` — §I-8 steps 1–4A, 6, 8; step 9 in `build/compile.py` |
| 1.4A | `rules/{parse,compile_rules}.py` |
| 1.5 | frames extended and conformance-tested, `emitter`, `compile`, `publish` |
| 2.1–2.3 | `canonical`, `dedup`, `relint`, `queues`, `cli/review.py` |
| 3.1–3.4 | `photo`, `continuation`, `figures`, `audit` |
| 4.1–4.2 | `ops/{nightly,locks,state,log}.py`, `bin/nightly.sh`, rclone sync/publish |
| 5.1 | `docs/FIELD-ONBOARDING.md` |

Every §I-10 command is wired: `bootstrap rules ingest extract validate build sync
run audit spotcheck review browse star edit relint status`.

## Three day-one breakages, all fixed

Revision 16 of the plan fixed exactly this class of defect once. Three more were
present, and the third is the serious one:

1. **`make check` failed on a fresh clone** with `ModuleNotFoundError: jinja2`.
   Both `check` and `bootstrap` assumed the project's dependencies were
   importable by the bare `python3`/`pytest` on PATH. The Makefile now runs
   through `uv run --extra dev` when uv is available, and `uv.lock` is tracked.
2. **The pre-commit guard on `generated/` was inert.** It skipped with a warning
   whenever the rule compiler was not importable by bare `python3` — the normal
   state on a fresh clone, which is exactly when it matters. It now runs through
   uv and fails rather than skipping.
3. **`src/knowledge_base/build/` was never in the repository.** `.gitignore`
   carried an unanchored `build/`, which matches at *any* depth, so the entire
   build package — `numbering_sim`, `frames`, `emitter`, `compile`, `publish`,
   including two of the four artefacts the plan lists as verified — was silently
   excluded. The working tree had the files; a clean clone did not, and failed
   with `ModuleNotFoundError: No module named 'knowledge_base.build'`.

   This was found by cloning the repository into a temporary directory and
   running `make bootstrap check` there, which is the only way to find it: every
   check run in the working tree passes. Every ignore path is now anchored to
   the root.

   The same absence explains a lint discrepancy — with the directory missing,
   ruff classified `knowledge_base.build` as third-party and demanded a
   different import order in a clean clone than in the working tree. isort's
   first-party list is now declared in `pyproject.toml` rather than inferred, so
   the gate cannot depend on which directories happen to exist.

---

## Three findings the owner should read

### 1. The rule documents do not parse straight into a substitution table

Plan §I-5A says the ALWAYS/NEVER lines "parse straight to `banned: {Y: X}`".
That holds for the single-sentence em-dash shape. It does **not** hold for the
documents as a whole, and the failure mode is the dangerous one: a parser that
associates each NEVER with the nearest preceding ALWAYS produces confidently
wrong rulings that would become automatic, corpus-wide rewrites.

Four real examples from `rules/fields/complex-analysis.txt`:

| Produced | Source | Why it is wrong |
|---|---|---|
| `domain → region` | §17.1 | The sentences say the opposite: "NEVER use *region* as a synonym for *domain*". |
| `function → an entire function` | §5.1 | The second quoted word explains the prohibition; it is not a second banned term. |
| `infinity → the` | §17.1 | Two ALWAYS clauses in one paragraph; the NEVER attached to the wrong one. |
| `counterclockwise direction → negatively oriented` | §7.2 | Two mandates, two prohibitions, paired in the wrong order. |

Extraction is now restricted to two shapes where the *author* stated the
association, guarded against substitutions that would rewrite their own
replacement (`entire`) or corrupt a mandated proper name (`transformation`
inside "linear fractional transformation"). The result for Complex Analysis is
**24 banned terms, every one verifiable against the document**, plus 61
proposals in `generated/lexicon/complex-analysis.candidates.yaml` carrying the
sentence each came from — none of them enforced.

**What this costs you:** one ruling sitting over ~60 proposals per field, which
is WP1.7's work anyway. **What it buys:** no silent rewrite of the corpus in a
direction the documents do not support.

Related: `Proof_Style.txt` is written in the same ALWAYS/NEVER shape but its
rulings are *frame templates*. Compiling it produced a store-wide substitution of
`Therefore → Hence`. It now compiles to none of the three mechanical targets and
reaches the system only through hand-written frames, as §I-5A intends.

### 2. Two emitter defects that only a real compile finds

The emitter wrote its own `<label>` on every item, but `math-item` in
`template-star.typ` already attaches one — **every document failed to compile**
with "label occurs multiple times". And escaping was being applied to frame
output, which stripped the bold markers Common §21.1 and Proof Style §4.3
mandate. Escaping now runs on slot text, before frames compose: the transcribed
half is the untrusted one, and frame markup is deliberate.

Both were found by compiling a real document with the vendored toolchain, not by
reading. Neither would have shown up in a test that only checked strings.

### 3. Phase 3's prerequisite still stands

The configured fields are Complex Analysis and Ordinary Differential Equations.
The material in Drive is a Complex Analysis textbook PDF plus roughly 200 board
photographs of **Linear Algebra and Abstract Algebra**, which are not configured
fields. Phase 3 is board-driven and, as configured, has nothing to ingest.

Reporting it here as the plan directs, not deciding it. The choice is:

- **promote Linear Algebra and Abstract Algebra to fields** — each needs a field
  rule document, roughly the length of `rules/fields/ode.txt`, plus a profile and
  two lines of config (`docs/FIELD-ONBOARDING.md` is the runbook); or
- **wait for board captures in a configured field.**

Building a book for a subject you did not ask for is the expensive mistake here.

---

## What is blocked, and on what

| Item | Waiting on |
|---|---|
| **WP0.3 (S1)** — extraction probe, dialect A/B, quad detection over the real photo set, text-height measurement | Drive + the real captures. Resolves B2, B10, B11, B13, B16, B17; first evidence for B12 |
| **WP0.4 (S2)** — budget | timing from a real WP0.3 run. Resolves B3 |
| **WP1.5 milestone** — chapter 1 ingested live, ToC outline approved | the Complex Analysis PDF |
| **WP1.6** — proof pilot | 20 real proofs. Resolves B7 for textbook proofs |
| **WP1.7** — lexicon seeding sitting | chapter-1 output, plus the 61 candidates already generated |
| **WP2.4** — overlap trial | a second Complex Analysis source (still outstanding on your checklist) |
| **WP3.5** — live lecture week | board captures in a configured field |
| **WP4.3** — Task Scheduler | a Windows desktop. Resolves B14 |
| **WP5.2** — ODE calibration | ODE material |

Nothing in that list is waiting on code.

## Standing caution

No extraction has ever been performed by this system. Every extraction-side
claim in this repository remains unverified, and every fixture here is generated
and labelled as testing plumbing rather than fidelity —
`tests/fixtures/make_captures.py` and the photo tests both say so in their
headers. `docs/SLICE-FINDINGS.md` records what it cost the last time generated
material was read as evidence.

## First three commands on the desktop

```
uv sync --extra dev && make bootstrap check    # verify the port
rclone sync gdrive:Mathematics/10-Source-Captures/Complex-Analysis inbox/complex-analysis --checksum
knowledge-base ingest complex-analysis && knowledge-base extract --limit 1
```

The third is the first call this system will ever make to a model. Read what it
returns before letting it run a second batch.
