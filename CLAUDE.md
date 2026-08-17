# CLAUDE.md

Working instructions for this repository. Read this before writing any code.

## What this is

A personal knowledge-base pipeline. Photographs of lecture boards, PDF pages, and
screenshots of textbook sections become a canonical store of typed items, which
renders to one typeset PDF per field of study. It is built once and used for
decades, across every subject its owner studies.

## Working protocol

Do one step at a time. The step is what the current instruction says, and nothing
more. When it is done, stop and report. Do not continue to the next piece of work,
do not start adjacent work that seems useful, and do not fix things you noticed
along the way — report them instead.

**Ask rather than decide.** If the instruction is ambiguous, or the specification
is silent, or two documents disagree, stop and report it. Do not choose a default
and continue. A choice made without the owner is a choice he cannot review while
changing it is still free.

**Reporting "Done" does not complete a step.** The owner tests the result and
approves it. Until then the step is open.

**Do not update `STATE.md` on your own initiative.** It is updated only when the
owner confirms a step is tested and approved, and only when the instruction says
to update it.

## Environment

**Settled: native Windows.** Not WSL2. The code is dual-platform — POSIX paths
are kept and tested — but this machine is Windows and that is where every claim
in this repository was verified.

Installed: `uv` 0.12.5, `typst` 0.15.1, GNU `make` 4.4.1 (all via scoop) and
`git` 2.55.0. Python is 3.12.14, managed by `uv`; the project's `.venv` uses it.

**Run everything through `uv`.** A bare `python` on PATH resolves to the
Microsoft Store stub, not an interpreter. Use `uv run --extra dev …`; `make`
does this for you.

`typst` is **not vendored**. It is installed by the package manager, found on
PATH, and its version is verified against `template/TOOL-SHAS.txt` — a mismatch
is a hard error. The fonts *are* vendored and still verified by sha256.

`rclone` is **not installed**. Anything that touches Google Drive — sync,
ingestion from captures, the nightly driver's first stage — cannot run yet.

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
   Part II is the build order as work packages and its owner-reviewed phase gates,
   Part III holds the decision register and the uncertainty register. When this
   file and the plan disagree, the plan wins.
2. **`rules/`** — four authored documents defining every notation, terminology,
   statement, and proof convention. Precedence: field file > Proof_Style >
   Common. Ownership headers are in `rules/Common.txt`. These are hand-edited by
   the owner; you may propose changes but never silently rewrite them.
3. **`docs/*FINDINGS*.md`, `docs/S3-RESULTS.md`** — what was learned by executing
   parts of this system on real material. Read before re-deriving anything.
4. **`STATE.md`** — where the work currently stands and what the open step is.
   Read it before starting anything. It is the only live status record; every
   other status statement in this repository is a dated historical report.

## What is already built

A large amount of this system is built and tested. `STATE.md` says what, and
`docs/SETUP-REPORT.md` (2026-08-04) records how it got there.

**Do not rewrite existing modules; extend them.** Where a module exists, it was
built against the specification and in several cases verified against the real
toolchain. If you believe one is wrong, say so and stop — do not replace it.

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

## Where to start

Read `STATE.md`. It names the open step. Do that step, and nothing beyond it.

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
make bootstrap              # fetch pinned fonts, verify sha256; verify typst's version
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
and frames must be updated. That test exists: `tests/test_frames_conformance.py`
reads the mandated strings out of `rules/` at test time and asserts that
`frames.py` emits them.

## One thing in the history to distrust

An earlier "vertical slice" was recorded as an extraction from a real lecture. It
was not — the content was hand-written, and the board photographs are a different
subject entirely. `docs/SLICE-FINDINGS.md` now states this. The consequence for
you: **no extraction has ever been performed by this system.** Treat every
extraction-side claim as unverified, and treat `tests/fixtures/synthetic/` as a
renderer regression fixture only, never as evidence about extraction quality.

