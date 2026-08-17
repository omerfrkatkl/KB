# Knowledge base pipeline

Converts photographed lecture boards, PDF pages, and screenshots of textbook
sections into a canonical store of typed items, and renders that store to one
typeset PDF per field of study.

The point is **exact consistency**. The same kind of information is always
expressed with the same sentence structure, the same terminology, and the same
notation, everywhere, permanently — because repeated structure is what makes the
material stick. That is achieved by keeping the probabilistic and deterministic
halves strictly apart: a language model reads sources and fills typed slots, and
ordinary Python composes every rendered sentence from fixed frames. No model
output is ever printed.

## Layout

```
docs/           the specification and the findings from executing parts of it
rules/          four authored documents defining every convention (hand-edited)
template/       the Typst template, its exam-star patch, pinned font hashes
prompts/        the extraction and audit prompt packs
src/knowledge_base/         implementation
tests/          test suite; fixtures/ holds real material used as golden cases
reference/      compiled PDFs proving the verified pieces work end to end
```

Created at runtime and not tracked: `inbox/` `derived/` `build/` `state/`
`logs/` `tools/` `fonts/`. Tracked but never hand-edited: `generated/`.

## Getting started

```
uv sync --extra dev     # or: pip install -e ".[dev]"
make bootstrap          # vendor pinned typst + fonts
make rules              # compile rules/ -> generated/
make check              # ruff + pytest
make hooks              # install the pre-commit guard
```

`make check` passes on a fresh clone. Before `make bootstrap` the tests that need
the compiler skip rather than fail.

Then `knowledge-base status` reports what is vendored, what is measured, what is
stored, and what is queued.

## State

Phases 0-4 of `docs/implementation-plan.md` are built as far as they go without
Google Drive: ingestion, the rule compiler, validation, the extraction runner
with record/replay, frames and the emitter, dedup, the queues and review CLI,
relint, the photo chain, continuation, figures, the audit stage, and the nightly
driver. `make check` is green from a clean clone.

**What remains is measurement, not code.** The four Phase-0 spikes need real
captures, and no extraction has ever been performed by this system — every
extraction-side claim here is unverified. Read `docs/SETUP-REPORT.md` for what
was executed, what it found, and what each remaining item is waiting on.

## Reading order

1. `CLAUDE.md` — the invariant, the hard rules, where to start
2. `docs/implementation-plan.md` — the specification
3. `rules/Common.txt` — precedence and ownership headers, then the rest
4. `docs/SETUP-REPORT.md` — the state of the build, its findings, and what each
   remaining item is blocked on
5. `docs/S3-RESULTS.md`, `docs/SLICE-FINDINGS.md`,
   `docs/RULE-INTEGRATION-FINDINGS.md` — what execution taught, including two
   schema gaps and several rule defects found only by running real material
   through the system
6. `docs/FIELD-ONBOARDING.md` — what "one-time setup per subject" concretely means
