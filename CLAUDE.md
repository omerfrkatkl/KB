# CLAUDE.md

Working instructions for this repository. Read this before writing any code.

## What this is

A personal knowledge-base pipeline. Photographs of lecture boards, PDF pages, and
screenshots of textbook sections become a canonical store of typed items, which
renders to one typeset PDF per field of study. It is built once and used for
decades, across every subject its owner studies.

## The invariant that defines the architecture

**A language model never writes a sentence that reaches the PDF.**

The model reads sources and fills typed slots. Deterministic Python composes every
sentence from fixed frames. This is not a style preference — it is the only way to
get exact structural and terminological consistency across an unbounded corpus
that grows for years. Anything else drifts.

If you find yourself about to let a model produce prose that will be rendered,
stop. You are dismantling the reason the system exists.

One deliberate exception exists and is already decided: `citation_form`, the
one-clause restatement of a result used after "by the fact that". It is authored
once per item, review-gated, then reused verbatim at every citation site. See
uncertainty B15 in the plan.

## Authoritative documents, in order

1. **`docs/implementation-plan.md`** — the specification. Part I is the system,
   Part II is the build order as work packages, Part III holds the decision
   register (25 resolved, none open unconditionally) and the uncertainty register
   (open, with the mechanism that resolves each). When this file and the plan
   disagree, the plan wins.
2. **`rules/`** — four authored documents defining every notation, terminology,
   statement, and proof convention. Precedence: field file > Proof_Style >
   Common. Ownership headers are in `rules/Common.txt`. These are hand-edited by
   the owner; you may propose changes but never silently rewrite them.
3. **`docs/*FINDINGS*.md`, `docs/S3-RESULTS.md`** — what was learned by executing
   parts of this system on real material. Read before re-deriving anything.

## Current state — what is already verified

These are not drafts. They were executed against the real toolchain and their
results are recorded. **Do not rewrite them; extend them.**

| Artifact | Status |
|---|---|
| `template/star.patch`, `template-star.typ` | exam-star marker, compiled and visually verified |
| `src/knowledge_base/build/numbering_sim.py` | at parity with `typst query` across chapters, stars, refs; B5 resolved empirically (`unnumbered_advances = false`) |
| `src/knowledge_base/build/frames.py` | Proof Style + Common §21 implemented in the renderer, every schema method covered; tied to `rules/` by `tests/test_frames_conformance.py`, which reads the mandated strings out of the documents at test time |
| `prompts/*.j2`, `src/knowledge_base/extract/prompts.py` | render deterministically; verified against a real three-capture batch |
| ingest · rules compiler · validation · emitter · build · dedup · queues · review CLI · relint · photo chain · continuation · figures · audit · nightly | built, tested offline, `make check` green |

**What is not built is not code — it is measurement.** The four Phase-0 spikes
(B1 at runtime, B3, B12, B16) need real captures and Google Drive, and no
extraction has ever been performed by this system. Every extraction-side claim
in this repository is unverified. `docs/SETUP-REPORT.md` states exactly where the
build stopped and why.

## Drive layout this repository expects

Created 2026-07-31. `config.yaml` holds the paths; the conventions are documented
in Drive at `Mathematics/READ-ME-Structure-and-Conventions`.

```
Mathematics/
  00-Knowledge-Base-Pipeline/{Repository,Specification,Rule-Documents,Run-Reports}
  10-Source-Captures/<Subject>/Lecture-Boards/
  10-Source-Captures/<Subject>/Texts/<Source-Name>/
  10-Source-Captures/<Subject>/Texts/Unsorted/
  20-Knowledge-Base/            <- built PDFs are published here
```

`Lecture-Boards` and `Texts` are how provenance `kind` is determined — never from
the image, because `kind` decides the exam star. Everything under
`10-Source-Captures` is immutable: it is the only path back from an item to the
pixels it came from.

## Running without interruption

The owner starts you once and expects setup to complete unattended. **Do not ask
questions.** `docs/AUTONOMY-PROTOCOL.md` is binding: every foreseen decision has a
default, every unforeseen one has a fallback ordering, and only three conditions
justify stopping. Record what you chose in `DECISIONS-TAKEN.md` and keep going.

Two consequences worth internalising. First, `make rules` runs before any
extraction — compiling the rule documents into the lexicon converts about 150
terminology rulings into decisions already made, and is the largest single
reducer of mid-run interruption. Second, a gap in the specification is not a
reason to stop; it is a reason to take the reversible option and log it.

## One thing to raise with the owner, once, before Phase 3

The configured fields are Complex Analysis and Ordinary Differential Equations.
The material in Drive is a Complex Analysis textbook PDF plus roughly 200 board
photographs of **Linear Algebra and Abstract Algebra**, which are not configured
fields. Phases 0 through 2 are textbook-driven and run fine on the PDF. Phase 3 is
board-driven and, as configured, has nothing to ingest.

Do not stop for this and do not guess. Carry on through Phase 2, and when you reach
Phase 3 report the choice: promote Linear Algebra and Abstract Algebra to fields
(each needs a field rule document, roughly the length of `rules/fields/ode.txt`),
or wait for board captures in a configured field. Building a book for a subject he
did not ask for is the expensive mistake here; the reversible one is to ask at the
point where it actually matters.

## If you are running as a cloud session

Cloud sessions are isolated VMs with no Google Drive access — only the first-party
GitHub integration is available, so `rclone`, the Drive OAuth flow, and every
capture in `inbox/` are out of reach. They also share the account's rate limits
with all other Claude usage.

What this means concretely:

- **Buildable here:** everything that does not need source material. WP0.1,
  porting the verified WP0.2 artefacts, the rule compiler (WP1.4A), models and
  store (WP1.1), validation, dedup, queues, the emitter, the frames conformance
  test, the CLI. That is the bulk of Phases 0–2 by volume.
- **Not buildable here:** ingestion from Drive, the extraction runner's live
  behaviour, the nightly scheduler, and any measurement that needs real captures
  (B1 fidelity at runtime, B3, B11, B12, B16).
- **Network:** `make bootstrap` and `pip` need `github.com`,
  `raw.githubusercontent.com`, `pypi.org`, and `files.pythonhosted.org` on the
  session's allowlist. If they are absent, that is hard stop 3 — report it rather
  than working around it with an unpinned toolchain.

Build what is buildable, drive it with tests rather than with real material, and
stop at the first stage that genuinely requires a capture. Do not simulate
captures to keep going: a fabricated fixture that looks like evidence is the one
failure this project has already had once, and `docs/SLICE-FINDINGS.md` records
what it cost.

## Where to start

**Read `docs/SETUP-REPORT.md` first.** Phases 0–4 have been built as far as they
go without Drive; that report says what was executed, what was found, and what
each remaining item is waiting on.

The next work is **WP0.3 and WP0.4**, the Phase-0 spikes, and both need a
desktop with Drive access. Everything downstream of them is built and waiting.

Phase 0 exists because four things are genuinely unknown and cannot be settled by
reasoning: board-photo extraction fidelity (B1), whether the weekly volume fits
the Pro subscription's limits (B3), continuation behaviour on real lecture flow
(B12), and the resolution floor below which subscripts are lost (B16). Do not
skip ahead of them. If a measurement contradicts the plan, the measurement wins —
report it and stop rather than building on a false premise.

## Hard rules

- **Never hand-edit anything under `build/` or `generated/`.** They are outputs.
  Fix the input and regenerate. A pre-commit hook enforces this.
- **Never add a dependency** outside the closed list in `pyproject.toml` without
  stating why in the commit message.
- **Never delete the unused environments** from `template/template.typ`
  (`#exer`, `#prob`, `#que`, `#solution`, `#note`, `#num-eq`). Decision A9:
  exclusion is enforced by the taxonomy and the emitter allowlist, which are
  deterministic. Deleting template code adds no enforcement and breaks the file
  for other uses.
- **Schemas extend, never change.** Decision A7. If real material does not fit a
  schema, add a field or a variant; never repurpose an existing one, and never add
  a free-prose escape hatch.
- **Never force content into the nearest type.** Unclassifiable material goes to a
  review queue. A forced fit is silent distortion and undetectable downstream.
- **Never invent a proof.** If a source asserts a result without argument, the
  item carries no proof and is completed later from another source.
- **Read the relevant rule document before touching `frames.py`.** Every string it
  emits traces to a numbered rule.

## Commands

```
make bootstrap              # fetch pinned typst + fonts, verify sha256
make check                  # ruff + pytest — the gate for every work package
make rules                  # compile rules/ -> generated/
make hooks                  # install the pre-commit guard
knowledge-base run          # one full pipeline pass
knowledge-base review       # work the decision queues
knowledge-base status       # what is vendored, measured, stored, queued
```

`make check` and `make bootstrap` run through `uv` when it is present, so a fresh
clone works after `uv sync --extra dev`.

The command is deliberately unabbreviated. Add a shell alias if the length annoys
you day to day; do not rename the entry point.

## A correction to the plan you should know about

Plan §I-5A lists four compilation targets for the rule documents: lexicon,
symbols, validators, and frames. The first three are mechanically compilable —
`ALWAYS X — NEVER Y` lines parse straight into substitution tables. **Frames are
not.** Frame logic is executable code with conditionals (six-way transition
selection, build-time membership checks, method-specific substructure); no regex
extracts that from prose, and generating it with a model at build time would
reintroduce the nondeterminism the architecture exists to remove.

So `src/knowledge_base/build/frames.py` is **hand-written Python that implements** Proof Style
and Common §21. The deterministic link to the documents is a **conformance test**:
the rule files contain many literal mandated strings ("Hence [conclusion].",
"Consider [n] cases.", "by the inductive hypothesis"), and `make check` must
assert that `frames.py` emits exactly those. When a rule changes, the test fails
and frames must be updated. That test does not exist yet — writing it is a good
early task, and it belongs in WP1.5.

## One thing in the history to distrust

An earlier "vertical slice" was recorded as an extraction from a real lecture. It
was not — the content was hand-written, and the board photographs are a different
subject entirely. `docs/SLICE-FINDINGS.md` now states this. The consequence for
you: **no extraction has ever been performed by this system.** Treat every
extraction-side claim as unverified, and treat `tests/fixtures/synthetic/` as a
renderer regression fixture only, never as evidence about extraction quality.

## Autonomous operation — do not ask questions during setup

The owner starts you once and does not answer questions while you work. Read
`docs/AUTONOMOUS-OPERATION.md` before beginning; it is binding.

The rule: **never ask — choose the documented default, log it to
`DECISIONS-TAKEN.md`, continue.** Every setup decision is either a documented
default, a measurable value with a stated procedure, or one of exactly three hard
stops (missing credential, a Phase-0 measurement contradicting the plan, or
threatened store corruption). A decision fitting none of those means this
documentation has a gap: take the conservative option, log it as
`UNDOCUMENTED-DEFAULT`, and keep going.

This applies to *setup*. It does not apply to content: unclassifiable material still
goes to a review queue rather than being force-fitted, because that is the one call
that cannot be reversed by regenerating. A filling queue is not a reason to stop.

If you find the plan is wrong, say so in your final report and propose the
correction — several sections exist because earlier assumptions were caught that
way — but correct course and continue rather than waiting.
