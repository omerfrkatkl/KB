# Personal Knowledge Base Pipeline — Implementation Plan

**Revision 18.** The runtime moves from WSL2 Ubuntu to native Windows, and `typst` stops being vendored. §I-1's host and toolchain clauses are rewritten accordingly; everything else in Part I, and all of Part II and Part III, is unchanged. The owner works in Windows and a system meant to last decades must be maintainable by him, so the POSIX-only assumptions were reworked rather than the owner moved: `store.py` keeps its content fsync and leaves the rename's durability to the OS (Windows has no directory fsync); every text-mode open carries `encoding="utf-8"` and every text-mode write `newline=""`, so files are written LF on both platforms as `.gitattributes` requires; `locks.py` uses `fcntl` on POSIX and `msvcrt.locking` on Windows behind one non-blocking `AlreadyRunning` contract, verified by a two-process exclusion test; queue entry ids are sanitised before becoming filenames on every platform, so `queue/` is identical across checkouts, while the id inside the file stays unsanitised; `bin/nightly.sh`, `bin/install-hooks.sh` and `bin/pre-commit` are recorded in git as mode 100755 (they were 100644 — a POSIX clone received them non-executable) and the test asserts the git-recorded mode rather than the filesystem bit; `install-hooks.sh` sets `core.hooksPath` instead of creating a symlink; the Makefile branches on `$(OS)` to detect `uv` and to resolve a real shell, because GNU Make on Windows runs `$(shell …)` through cmd.exe; and `make clean` is now `src/knowledge_base/ops/clean.py`. The code is dual-platform, not Windows-only. Suite: 272 passed, 0 skipped, 0 failed; every `make` target works. `rclone` is not installed, so the Drive-facing stages remain unrun. Both decisions are recorded in `DECISIONS-TAKEN.md`, dated 2026-08-17.

**Revision 17.** The autonomous-operation layer introduced in revision 13 is removed. It contradicted PART II, whose phase gates were owner-reviewed from revision 4 and were never changed to match: "you review scorecard", "you read the chapter-1 PDF end-to-end and accept every item", "overlap trial report accepted". The two protocol documents it added, `docs/AUTONOMY-PROTOCOL.md` and `docs/AUTONOMOUS-OPERATION.md`, also disagreed with each other — different hard-stop lists, and two different procedures for the same measurement (`resolution_floor_px` at the 5th percentile in one, the 10th in the other). Both are deleted; §I-13 is now the working protocol, one step at a time under owner approval. PART II is unchanged. `STATE.md` is introduced as the single live record of position, and `DECISIONS-TAKEN.md` continues as the append-only record of why each decision was made.

**Revision 16.** Runnability pass on the prepared repository. Two day-one blockers found and fixed: `make bootstrap` called a module that was never written, and `make check` failed with 144 lint errors — both commands in the README's getting-started block were broken. `ops/bootstrap.py` now exists and has been executed end to end (typst 0.15.1 and six fonts fetched, hashed, pinned, re-verified, idempotent on re-run); ruff carries an explicit rule set and the genuine defects are fixed rather than silenced; a minimal `knowledge-base` CLI makes the declared console script resolve and reports which work package builds each pending stage. Full suite green including the parity test, which previously skipped for want of a toolchain. A26 resolved. Also flagged: the configured fields hold no board captures, which gates Phase 3 and nothing earlier.

**Revision 15.** A27 resolved: colour carries no meaning in v1, and the prompt's colour heuristic is removed in favour of "judge every region by what it says" — a simplification, since a heuristic that fires on emphasis would have mis-routed content the lecturer merely wanted to highlight. Also corrected an error in revisions 13–14, which claimed no register entry could block an unattended run while A26 was open with no default: A26 now carries one, and the claim is true as stated.

**Revision 14.** A28 resolved as an exclusion: source errata become `source-correction`, a new class in the shared exclusion vocabulary. No new item type — the taxonomy stays at the pure-information set. Because both prompts render their exclusion list from `taxonomy.excluded`, the class reached the extractor and the auditor from a single edit, and the shared-vocabulary test proves it. A27 is the only register entry still open, and its pre-recorded default means it cannot block an unattended run.

**Revision 13.** Zero-interaction setup specified: `docs/AUTONOMY-PROTOCOL.md` (never ask; documented default, else fallback ordering; three hard stops only; measurements taken not requested) and `DECISIONS-TAKEN.md` (autonomous choices logged for later review, with pre-recorded defaults for every open register item). Phase gates are self-certifying against a completion checklist rather than owner-reviewed mid-run.

**Revision 12.** Twenty real board photographs read directly (docs/BOARD-CONTENT-ANALYSIS.md (now docs/FINDINGS.md)) — the project's first content-grounded evidence. One stated assumption broken: a fully-visible board from a *different course* shared the frame, which the "ignore clipped content" rule cannot catch; new `foreign-subject` exclusion class added to taxonomy and both prompts. Also: consecutive photographs overlap far more than assumed (dedup load from day one), board content is labelled where textbook prose is not, and a real counterexample of the A12 hypothesis-necessary kind was observed. Plus the zero-interaction startup protocol (§I-13).

**Revision 12.** Twenty real board photographs read (docs/BOARD-EXTRACTION-FINDINGS.md (now docs/FINDINGS.md)) — the first actual content analysis in this project. B1 resolved: legibility is not the problem. B7 partially resolved and the schema extended: real proofs required `double-inclusion` and `verify-criteria` methods and a `sufficiency` setup form. Three unanticipated behaviours found and specified into the extraction prompt: a fully visible board can belong to a different course, boards are corrected in place, and coloured chalk carries meaning. New: **[A27]**, **[A28]**.

**Revision 11.** Real capture corpus analysed (200 board photographs across two subjects, docs/CAPTURE-CORPUS-ANALYSIS.md (now docs/FINDINGS.md)). One defect found and corrected: session grouping keyed on upload timestamps merges distinct lectures — in the worst real case, five lectures inside fifteen minutes. Grouping now resolves session identity by explicit precedence with a flagged fallback (**[A26]**). Volume measured at ~38 photographs/week for two subjects, making the 200/week planning figure ~2.6x conservative. Batching parameters confirmed adequate.

**Revision 10 — CORRECTION.** The "vertical slice" recorded in revisions 3–5 as an extraction from a real 2026-05-03 lecture was not one: the board photographs are Linear Algebra, the slice content is Complex Analysis, and the items were hand-written. Consequences: **B7 is untested**, **B12 has no first evidence**, and the `iff-pair` proof method plus the by-fact/pending-ref routing rule were invented rather than observed — they remain in the schema as reasonable additions but carry no empirical provenance. The deterministic machinery verified alongside it (star patch, numbering parity, arrow codepoints, frames-as-code, rule-document edits) is unaffected; those were checked against the real compiler and real documents. See docs/SLICE-FINDINGS.md (now docs/FINDINGS.md).

**Revision 9.** Repository assembled for handoff (kb-repo.zip): every verified artifact placed at its spec path, scaffold added, suite green on a fresh clone. Two corrections this surfaced — `jinja2` was missing from the closed dependency list, and frames cannot be *generated* from the rule documents; they are hand-written and **conformance-tested** against them (I-5A).

**Revision 8.** A25 resolved and written into the ingestion spec (not just the register). The decision register now holds no open unconditional items: every architectural and stylistic question raised across revisions 1–8 is settled, and what remains is measurement (Phase 0) and construction.

**Revision 7.** Full-document audit pass. Three edits from revisions 5–6 had silently failed to apply (their search strings no longer matched after intervening rewrites) and are now in place: the `kind × capture` provenance model, the extended justification-kind list, and the `rules/` + `generated/` directories. Also: superseded v0 frame wording deleted (it contradicted the live spec), module map and config reconciled with revisions 5–6, `capture_id` threaded through both LLM contracts, raster given a work package in Phase 1, and the A13 open/resolved contradiction in the register removed. Every edit in this pass was assertion-checked.

**Revision 6.** Adds the third input path — flat raster captures (screenshots of PDF pages or sections) — by splitting the conflated source axis into `kind` (semantic) × `capture` (geometric), per A23/A24. Ordering is now content-driven and file-metadata-independent. New: resolution gate, capture groups, **[B16]**.

**Revision 5.** Absorbs the four rule documents (Common, Proof Style, Complex Analysis, ODE) as a first-class architectural layer: they are the authored source of truth from which lexicon, symbol registry, frames, and validator rules are all generated (new §I-5A). A16–A22 resolved and compiled into `frames_v1.py`; verified by re-rendering the 2026-05-03 lecture (artifacts: kb-rulecompliant-artifacts.zip). New uncertainty: **[B15]**.

**Revision 4.** Expansion of rev 3 to implementation granularity. Architecture and all prior rulings (A1–A12) unchanged; this revision adds full technical specification (Part I), a work-package build sequence (Part II), and updated registers (Part III). New items requiring input: **[A13]**; new uncertainties: **[B13] [B14]**. Structure reorganized into Parts; rev-3 section numbers no longer apply.

Consumers: you (Part III inputs; acceptance gates in Part II) and Claude Code (everything).

---

# PART I — SYSTEM SPECIFICATION

## I-1. Runtime, tooling, conventions

- **Host (revised, revision 18):** native Windows. Python 3.12, managed by `uv`; a bare `python` on PATH is the Microsoft Store stub, so everything runs through `uv run --extra dev …` and `make` does that for you. `uv` for env + lockfile; `ruff` (lint + format); `pytest`. `make check` = ruff + pytest and is the gate for every work package. The code stays dual-platform — POSIX branches are kept and tested — but Windows is the host every current claim was verified on. `rclone` is not yet installed, so nothing that reaches Google Drive can run.
- **Dependencies (closed list):** `pydantic` v2 (all data models; JSON Schemas for prompts are generated from these models — single source of truth), `ruamel.yaml` (round-trip YAML), `pymupdf`, `opencv-python-headless`, `rapidfuzz` (similarity scoring), `typer`, `rich`, `python-ulid`, `jinja2` (prompt-pack templates — added 2026-07-30; the packs need it and the original list omitted it). Additions require a stated justification in the commit.
- **Toolchain pins (revised, revision 18):** `typst` is **not vendored**. It is installed by the system package manager, found on PATH, and its reported version is verified against `template/TOOL-SHAS.txt` by the bootstrap script; a mismatch is a hard error. The version, not the hash, is what matters — `build/numbering_sim.py` reproduces the numbering behaviour of one specific release, and a release that changed it would emit wrong reference numbers rather than fail. The fonts **are** vendored (`fonts/`: Fira Sans, Fira Math from official repos), fetched by the same script and pinned by sha256 in the same file, because they are not packaged and `--font-path fonts/` deliberately bypasses system fonts. Builds always use `--font-path fonts/`.
- **Claude Code:** installed and logged in on the host (your existing install). The pipeline shells out to it; it is never a Python dependency.
- **Git policy (A13, resolved):** the repo tracks store, profiles, prompts, assets (figure crops), code, tools/fonts manifests. It does **not** track `inbox/` originals or `build/` outputs (gitignored). Consequence: the permanent archive of original photos/PDFs is **Google Drive + the local `inbox/` mirror**, not git. Any additional backup of originals (third location) is outside this system's scope — confirm you accept this archive policy, or name the additional mechanism you want documented.
- **Pre-commit hook:** rejects manual diffs under `build/`; runs ruff on staged Python.
- **Provenance of the pipeline itself:** every extraction batch records `extractor: {cli_version, model?, prompt_hash, dialect}` (envelope-reported fields where available) into the items it produced — so any future quality question can be traced to the exact prompt version and model that produced an item. Prompt changes never trigger automatic re-extraction.

## I-2. Repository layout and module map

```
kb/
  config.yaml
  Makefile  bin/nightly.sh
  fields/<field>/profile/{taxonomy,lexicon,symbols,outline,sources}.yaml
  fields/<field>/items/<ulid>.yaml
  fields/<field>/assets/<ulid>/fig-<n>.png
  inbox/<field>/boards/…     # gitignored; immutable originals, mirrors Drive (A23)
  inbox/<field>/books/<source-key>/…
  derived/<field>/…          # gitignored; board crops, page renders, text layers
  queue/<queue-name>/<id>.yaml
  state/{progress.json, batches/, calls/}    # calls/ = record/replay log
  build/<field>/{main.typ, symbols-gen.typ, <Field>.pdf}
  template/{template.typ, star.patch}
  prompts/{extract.md.j2, audit.md.j2}       # versioned; hash = prompt_hash
  rules/                     # AUTHORED source of truth (hand-edited; I-5A)
    Common.txt  Proof_Style.txt
    fields/complex-analysis.txt  fields/ode.txt
  generated/                 # DERIVED from rules/ — never hand-edited
    lexicon/<field>.yaml  symbols/<field>.yaml  validators/<field>.yaml
  tools/  fonts/  logs/  src/  tests/
```

```
src/knowledge_base/
  config.py                    # Settings (pydantic) ← config.yaml
  models/{item.py, slots.py, profile.py}
  ingest/{sync.py, registry.py, route.py, photo.py, raster.py,
          resolution.py, pdfdoc.py, groups.py}
  extract/{batcher.py, prompts.py, runner.py, replay.py}
  pipeline/{validate.py, canonical.py, dedup.py, continuation.py,
            audit.py, store.py, queues.py}
  build/{numbering_sim.py, frames.py, emitter.py, compile.py, publish.py}
  #  frames.py is hand-written, conformance-tested against rules/ (I-5A)
  rules/{compile_rules.py}     # rules/ → generated/ compiler
  cli/{main.py, review.py, browse.py}
  ops/{nightly.py, report.py, state.py, locks.py, log.py}
```

`config.yaml` (illustrative):

```yaml
fields:
  complex-analysis: {drive: "Mathematics/10-Source-Captures/Complex-Analysis", title: "Complex Analysis"}
  #   each field's Drive folder contains boards/ and books/<source-key>/ (A23)
  ode:              {drive: "Mathematics/10-Source-Captures/Ordinary-Differential-Equations",             title: "Ordinary Differential Equations"}
drive_remote: gdrive
output_folder: "Mathematics/20-Knowledge-Base"
budget: {max_pages_per_night: 0}        # set by S2
batching: {pdf_pages: 8, board_crops: 6, raster_captures: 6}
groups: {session_gap_minutes: 45}        # board × photo only
resolution_floor_px: 0                   # median text height in px; set by B16
dedup: {auto_confirm: 0.93, queue_floor: 0.75}   # tuned Phase 2
dialect: typst                           # or latex — set by S1 (B13)
model: default                           # optional pin for claude -p
```

## I-3. Data model

**Item file** (`fields/<field>/items/<ulid>.yaml`):

```yaml
id: 01J9X…                # ULID (creation-time sortable)
schema_version: 1
field: complex-analysis
type: theorem             # taxonomy key
slots: {…}                # per-type; see below. `form` lives in the definition
                          #   slots, not at item level — one home per field.
title: "Rouché's Theorem" # optional → template title:
terms_used: [holomorphic, winding-number]
topic: cauchy-theory
order: null               # optional manual override within topic
exam_star: auto           # auto | true | false; auto ⇒ true iff any provenance.kind == board
status: active            # active | open | flagged | superseded
superseded_by: null
refs: [<ulid>, …]         # union of {ref:…} tokens in slots
provenance:                 # append-only; kind × capture are independent (I-3 below)
  - {source: brown-churchill-9e, kind: textbook, capture: pdf, page: 153,
     region: [x,y,w,h], image_sha256: …, group: bc9e-pp150-158,
     extractor: {cli_version: …, model: …, prompt_hash: …, dialect: …}}
  - {source: brown-churchill-9e, kind: textbook, capture: raster, locator: "§54",
     page: null, region: […], image_sha256: …, group: drop-2026-07-29a}
  - {source: ca-lectures-2026s, kind: board, capture: photo, locator: null,
     group: 2026-05-03, photo: …, region: […], image_sha256: …}
figures: [{asset: fig-1.png, caption: null,
           origin: {provenance_index: 0, bbox: […]}}]   # indexes into provenance[]
created: …  updated: …
```

**Status machine:** `open` (schema-incomplete, awaiting continuation) → `active` (complete, builds) ; any → `flagged` (in a queue, excluded from builds) → `active` on resolution; `superseded` terminal (kept for provenance, never built).

**Slot text grammar (STG)** — the only content format allowed inside prose slots: plain Unicode text; inline math delimited `$…$` (dialect per config, B13); reference tokens `{ref:<ulid>}`; nothing else — no markup, no lists, no line breaks unless the field is typed as a list. Validator enforces balanced `$` and resolvable/pending ref tokens. All styling belongs to the template; all sentence structure belongs to frames (I-11).

**Per-type slots:**

- `definition`: `term` (STG, no refs), `form` (noun|predicate), `article` (a|an|the|none — noun form; unique objects take "the"; possessive/proper-name terms such as *Laplace's equation* take none), `subject?` (predicate form: the object being qualified), `context?` (ambient assumptions), `body`.
- `theorem | lemma | proposition | corollary`: `name?`, **`citation_form`** (REQUIRED, A21 — the result as a single subordinate clause usable directly after "by the fact that", e.g. "the real and imaginary parts of an analytic function are harmonic in its domain"; see [B15]), `hypotheses[]` (each STG), `conclusion`, `proofs[]` (below; **may be empty** — sources legitimately state results without argument; empty does *not* mark the item `open`; proofless items are listed by `knowledge-base status` and complete later via dedup merge or manual supply), `converse_holds?` (true|false|unknown).
- `claim`: `body`, `citation_form` (REQUIRED, A21), `proofs[]?`.
- `counterexample` (A12): `target` (ulid), `establishes` (converse-false | hypothesis-necessary), `hypothesis?` (required iff hypothesis-necessary), `witness`, `witness_properties`. Rendered via `#claim`.
- `axiom`, `notation`, `remark`: `body` (one fact per item; extraction rule).
- **proof** object: `method` (direct | contradiction | contrapositive | induction | strong-induction | construction | cases | uniqueness-pair | iff-pair | double-inclusion | verify-criteria | computation), `setup?`, `steps[]`, and method substructures: induction/strong-induction ⇒ `base{steps[]}` + `inductive{hypothesis, steps[]}`; cases ⇒ `cases[{condition, steps[]}]`; uniqueness-pair ⇒ `existence{steps[]}` + `uniqueness{steps[]}`; iff-pair ⇒ `forward{steps[]}` + `backward{steps[]}` (rendered (⇒)/(⇐); added 2026-07-20 on reasoning, not from observed material); **double-inclusion** ⇒ `subset{steps[]}` + `superset{steps[]}`, either block permitted to be a single dismissal such as "always true" (rendered (⊆)/(⊇) — added 2026-08-01 from an observed proof of `IJ = I∩J`); **verify-criteria** ⇒ `definition` (the definition being checked) + `criteria[{name, steps[]}]`, where completeness of the list is the proof (added 2026-08-01 from an observed proof that an arbitrary intersection of ideals is an ideal). `setup` additionally accepts a **sufficiency** form, rendered `It is enough to show that ⟨…⟩.`; then `conclusion`. Each step: `{claim, justification:{kind, term?, ref?, fact?, content?, transition?}}` where `kind` ∈ `by-hypothesis | by-inductive-hypothesis | by-definition | by-ref | by-fact | by-computation | by-mechanical | by-previous-step`; `term` iff by-definition, `ref` iff by-ref (and optionally on by-fact/by-definition, which is what makes A20's build-time membership check possible), `fact` iff by-fact, `content` iff by-previous-step, `transition` optional and carries "Note that" / "Similarly" / "Moreover" (Proof Style §3.2).

Schema evolution: **extend-only** (A7). `schema_version` bumps on extension; old items remain valid by construction; no migrations.

## I-4. Canonicalization, dedup, similarity

**Canonical form** of an item (for hashing and matching), computed per slot then concatenated with the type tag:
1. substitute canonical terms via the lexicon map (longest-match, word-boundary, case-folded) in prose runs;
2. lowercase prose outside math;
3. collapse whitespace;
4. math runs: strip internal spaces and apply a small command/alias synonym table (maintained in `canonical.py`; textual normalization only — symbolic equivalence is out of scope and documented as such);
5. sha256 → `canonical_hash`.

**Dedup pass (per accepted item):**
- exact `canonical_hash` match in field → auto-merge: append provenance, union `terms_used`/`figures`, keep existing slots; no new item.
- extractor `duplicate-of` proposal + RapidFuzz token-set ratio ≥ `auto_confirm` on normalized statement slots (`conclusion`+`hypotheses` or `body`) → auto-merge as above.
- **subset match** (review repeats): new item's normalized statement is contained in an existing item's (statement-only restatement of a fuller item) → auto-merge, content unchanged.
- ratio in `[queue_floor, auto_confirm)`, or proposal below threshold → near-duplicate queue (options: merge-keep-A / merge-keep-B / keep-both / keep-both-proofs — the last appends the new proof into `proofs[]`).
- below `queue_floor` and unproposed → distinct item.
Thresholds start conservative and are tuned in Phase 2 (B6).

## I-5. Profiles

- **taxonomy.yaml:** ordered list of type keys with `render: <template-fn>`, `numbered: bool`, `schema: <model name>`. The emitter allowlist *is* this file. Excluded-by-policy content classes (question, problem, solution, worked-demonstration, recall-repeat, non-content) are listed here too, as `excluded:` entries with one-line definitions — this block is embedded verbatim in both prompts, so extractor and auditor share one written policy.
- **lexicon.yaml:** `canonical:` list (term, optional casing rule, optional scope note) + `banned:` map (variant → canonical). Linter semantics: tokenize prose runs (math excluded); any banned token ⇒ deterministic substitution *at validation time* with log entry; any technical-looking unknown term reported by the extractor's `terms` output and not in `canonical:` ⇒ new-term queue (item proceeds to `flagged` only if the unknown term is load-bearing in a statement slot; otherwise item passes and the term queues independently).
- **Retroactive enforcement — `knowledge-base relint`:** on any lexicon ruling, re-run substitution across the whole store; word-boundary exact replacements auto-apply and commit (`relint: <ruling>`); ambiguous hits (inside math, casing conflicts) queue instead. Then rebuild. This is what makes requirement-4 consistency hold across time, not just forward.
- **symbols.yaml:** registry entries → emitted `#let` bindings in `build/<field>/symbols-gen.typ` (extends the template's `Re/Im/Arg/Log/Res`). Notation changes = one registry edit + rebuild.
- **outline.yaml:** `chapters: [{key, title, topics: [topic-key,…]}]`. **Ordering policy within a topic:** explicit `order` if set; else sort key = (source rank, page, region-y) of the first *textbook* provenance with a known page; a raster capture has no page, so it falls back to (source rank, group first-seen, region-y); board-only items follow, ordered by (group datetime, capture index). Self-correcting via `order` whenever you dislike the flow.
- **sources.yaml:** `{key, kind: textbook|board, title, citation?, rank, conventions?}` — `kind` takes the same two values as `provenance.kind` (I-3), with no third spelling anywhere in the system. `rank` feeds the ordering key and the near-duplicate CLI's default suggestion (textbook first). `conventions` is a free-text typographic profile embedded in that source's prompts (e.g., for Brown & Churchill: "bold-italic marks a term being defined; results are referenced by display-equation number (n); many proofs are deferred to exercises"). One-time per source, per the onboarding philosophy.

## I-5A. Rule documents — the authored source of truth

Four hand-written documents (~700 ALWAYS/NEVER/IF rules) define every convention. They are
**authored** by you and **compiled** by the pipeline into four machine artifacts. One direction
only; nothing generated is ever hand-edited, so the documents can never drift from the system.

**Field split kept, consumer split added.** `Complex Analysis.txt` and `ODE.txt` map onto
`fields/<field>/`. `Common.txt` and `Proof_Style.txt` are compiled by *destination*, because a
rule's destination — not its topic — determines what enforces it:

| Destination | Rule classes | Enforcement | Bulk source |
|---|---|---|---|
| **Frames** (`src/knowledge_base/build/frames.py` — hand-written; see the correction below) | every rule governing generated prose: transitions, justification format and placement, openings, closings, proof-type structure, **and the statement forms** | *compiled in* — violation is impossible, not merely detected | Proof Style §2–§7 (proofs); Common §21 (definitions, theorem statements, citation form, counterexamples) |
| **Lexicon** (`generated/lexicon/`) | canonical/banned term pairs | validator substitution + `knowledge-base relint` | CA + ODE, nearly entirely |
| **Symbols** (`generated/symbols/`) | notation forms, operators, delimiters | symbol lint + `symbols-gen.typ` | CA + ODE, Common §2–§12 |
| **Validators** (`generated/validators/`) | checks on *transcribed slot content* | your existing regex engine | Common §13, §14, §18, §19 |

**The regex engine's role changes and moves earlier.** In the prior project an LLM wrote prose
and regex caught violations. Here deterministic code writes every sentence, so for prose-level
rules the frames *are* the enforcement and a regex pass over generated output is a **regression
test** — it must always pass, and any failure is a frame bug, never a content bug. The engine's
live job is checking **slot content**, the only text an LLM produces, at per-item validation
(I-8 step 4A), before storage. Both roles are kept: regression on output, enforcement on input.

**Why frames must own the proof rules.** Proof Style §3.2 selects a transition word by asking
whether a named justification was applied — semantic, and undecidable by regex over finished
prose. The item schema already carries that fact in `justification.kind`, so the choice is a
lookup, not an inference. Rule document and slot schema were independently designed around the
same distinction; compiling one into the other is the natural join.

**Correction (2026-07-30): frames are not compiled, they are conformance-tested.**
Lexicon, symbols, and validators compile mechanically. Frame logic does not: it is
executable code with conditionals — six-way transition selection, build-time
membership checks, method-specific substructure — and no regex extracts that from
prose, while generating it with a model at build time would reintroduce exactly the
nondeterminism this architecture exists to remove. `src/knowledge_base/build/frames.py` is
therefore hand-written Python implementing Proof Style and Common §21, and the
deterministic link to the documents is a **conformance test**: the rule files carry
many literal mandated strings ("Hence [conclusion].", "Consider [n] cases.", "by the
inductive hypothesis"), and `make check` asserts that frames emits exactly those, so
a rule change fails the build until frames is updated. That test belongs in WP1.5 and
does not yet exist.

**Compilation is mechanical for the other three.** 77 lines are already in literal `ALWAYS X — NEVER Y` shape and
parse straight to `banned: {Y: X}`. The field documents' §16/§18 theorem-name lists become the
named-citation table that A16 resolves against.

**Document state.** The four documents were edited 2026-07-29 (kb-rules-edited.zip, CHANGELOG.md):
precedence and ownership headers added, six contradictions resolved, five redundancies collapsed
to a single owner, nine defects corrected, and the statement-form gap filled as Common §21.
`[MOVED]`/`[MERGED]` stubs preserve section numbering, so a compiler keyed on section numbers
stays valid. The compiler MUST treat a stub as empty and follow its pointer, never parse it.

## I-13. Working protocol

Work proceeds one step at a time under owner approval. The coding agent implements
exactly what the current instruction specifies, stops, and waits. It does not
continue to the next work package, does not begin adjacent work it judges useful,
and does not decide questions the instruction leaves open — it reports them and
stops.

An open question is reported, not resolved. Where this plan is silent or
ambiguous, state the ambiguity and the options in the final report and stop.
Choosing a default and continuing is what this protocol exists to prevent: a
choice made silently is a choice the owner cannot review at the point where it
still costs nothing to change.

Completion is established by the owner testing the result, not by the agent
reporting success.

This covers how work is sequenced. It does not change how content is handled:
unclassifiable material still routes to review queues, because force-fitting it
is the one error regeneration cannot repair (A7, A12, §8.1). Queues are made rare
rather than removed, chiefly by pre-seeding the lexicon from the rule documents in
WP1.4A — roughly 150 canonical/banned pairs that become rulings never needing to
be asked.

Phase gates are defined in PART II and are owner-reviewed. A gate script that
checks evidence may support that review; it does not replace it.

## I-6. Ingestion

1. **Sync:** `rclone sync <remote>:<field.drive> inbox/<field> --checksum` per field; then `rclone copy` of `build/*/​*.pdf` + `report.md` → `<remote>:Mathematics/20-Knowledge-Base` at pipeline end.
2. **Registry:** every new file: sha256, EXIF dump (all images — camera tags also decide `capture`, step 3), size, mtime, first-seen timestamp (defines raster capture groups) → `state/progress.json`; identical hashes are never reprocessed. First file from an unknown source → new-source queue (one-time metadata; for PDFs the extractor's ToC pass proposes title/citation).
3. **Routing (`route.py`).** `kind` from the folder (A23): `<field capture folder>/Lecture-Boards/**` → board; `<field capture folder>/Texts/<Source-Name>/**` → textbook, with `<source-key>` supplying the source identity that filenames cannot (A25). A capture dropped in `Texts/Unsorted/` is ingested normally but its provenance `source` is held null and the whole drop raises **one** `unsorted-source` queue entry naming the files; answering it assigns the source and rewrites those provenance entries. Items from an unsourced capture are `flagged` until then, so nothing unattributed can reach a build. `capture` from the file: `.pdf` → pdf; image carrying EXIF camera tags (Make/Model) → photo; image without → raster. No filename pattern is ever parsed — device naming is arbitrary and must not be relied on.
3a. **Photo chain (`photo.py`):** EXIF orientation → board-quad detection (grayscale → bilateral filter → adaptive threshold + Canny → contour extraction → convex quad approximation → area/aspect filters → keep full quads, discard edge-clipped ones) → perspective-warp each board crop → CLAHE contrast. Failure (no confident quad) → fall back to whole image + a per-image flag; extractor prompt always carries the ignore-edge-clipped-content instruction. Derived crops → `derived/`, originals untouched.
3b. **Raster chain (`raster.py`)** — for flat captures (screenshots of a PDF page or section). Preprocessing is deliberately **empty**: no orientation fix, no quad detection, no deskew, no perspective warp, no CLAHE. The pixels are already rectified and high-contrast; every one of those operations can only degrade them, and quad detection in particular risks locking onto a figure box or table border and silently cropping content away. The image passes through untouched except for the resolution gate below. A raster capture may cover a fragment of a page, may overlap another capture, and carries no page identity — all three are absorbed downstream (item-level dedup merges overlaps; `locator` records whatever the capture shows).
3c. **Resolution gate (`resolution.py`, all image captures).** Estimate median text height (connected-component analysis on the binarized image); below the configured floor, the capture is routed to review rather than extraction. This is the one preprocessing step raster gets, and it guards the failure mode that hides best: a phone-resolution capture of a dense expression where a subscript or prime is simply not present in the pixels. Applies to photos too. Threshold measured in Phase 0 — **[B16]**.
4. **PDF chain (`pdfdoc.py`):** per page: 300 dpi render + text layer + lossless embedded-image extraction (for figure fidelity, I-11). Born-digital text layer accompanies the image in the prompt; the image remains ground truth.
5. **Capture groups (`groups.py`)** — generalizes the former board-only "session" so continuation (§7.3) works for every source kind:
   - **board × photo** — session identity resolved by explicit precedence, because upload timestamps demonstrably do not carry it (docs/FINDINGS.md, "Session grouping and volume": one real upload batch merged five lectures inside fifteen minutes):
     1. a dated subfolder under `Lecture-Boards/`, if present — structural and unfalsifiable;
     2. else EXIF `DateTimeOriginal` read from the file bytes (B10);
     3. else a parseable date in the filename — verified correct on 200/200 board photographs, and note that the standing rule against parsing filenames was given about *screenshots*, which have no shared convention across devices;
     4. else the file timestamp, **with a warning raised** — this is known-wrong and exists only so a run never halts.

     **Resolved once, then persisted (A26).** The session a capture belongs to is
     derived at first ingestion and written into the registry. Later runs read it
     and never re-derive it. This matters because the signals are not stable over
     a lifetime: a new phone may stop writing EXIF, a capture app may change its
     filenames, and a file copied between machines loses its timestamp. Re-deriving
     would silently regroup years-old captures and break continuation links that
     were correct when made. Dated subfolders are *supported* wherever they appear
     but never required — the owner does not have to change how he photographs.
     `session_gap_minutes` applies only within step 2. Capture order within a group is the sequence index where one exists, else the resolved timestamp.
   - **textbook × pdf** — contiguous page runs within one document.
   - **textbook × raster** — one group per **sync drop** (the set of new files observed in a single sync run, from the registry's first-seen timestamp). This is deterministic and independent of filenames and of file timestamps.

   **Ordering is not a correctness dependency for textbook-kind captures.** Placement in the book comes from `topic` + `outline.yaml` (I-11.1), never from ingestion order; continuation matches fragments by content against the open-item set (§7.3), never by file adjacency. A drop of screenshots in arbitrary order therefore produces the same book as the same drop in perfect order. If a fragment is processed before its parent, the two merge in whichever direction they meet — the merge machinery is symmetric. Group membership affects only extraction-context quality (related captures share a call), never the result.

   **Cross-device duplicates.** The same page captured on two devices yields different bytes and different names, so file-hash dedup will not catch it; item-level canonical-hash and near-match dedup (I-4) will, merging provenance across both captures. This is the expected path, not a failure.

## I-7. Extraction

**Batching:** by capture group (I-6.5). `textbook × pdf` — contiguous page runs of ≤ `batching.pdf_pages`. `board × photo` — ≤ `batching.board_crops` crops per group, in capture order. `textbook × raster` — ≤ `batching.raster_captures` per drop, arbitrary order (ordering is not a correctness dependency, I-6.5).

**Context pack per batch:** taxonomy + excluded-classes block; JSON Schemas (generated from pydantic); full lexicon; symbols; trailing ≤10 items from the same source and capture group (continuity); the **open-item set** for the field; a compact item index (id, type, title, statement digest ≤ 200 chars) for duplicate proposals; the source's **identifier→ULID table** — theorem/lemma numbers, display-equation numbers such as "(2)", section identifiers such as "Sec. 1" — so "by Theorem 2.4" or "by (2)" resolves to a stable ref (textbooks). Token budget guard: index truncated oldest-first if the pack exceeds a configured size.

**Prompt pack.** Built and verified 2026-07-30 (kb-prompt-packs.zip): `extract.md.j2` (16 sections), `audit.md.j2`, `assemble.py`, and 9 regression tests. Rendered against a real three-capture batch the pack costs ~4,200 tokens for extraction and ~1,300 for audit — the figure to watch if B3 proves tight, with sections 10–13 (open items, item index, identifier table, trailing context) the compressible parts. Three design points are load-bearing:
- **StrictUndefined**: a missing context variable raises instead of rendering a blank section. A prompt that silently lost its exclusion policy would produce plausible wrong output for a whole batch; failing the call is strictly better.
- **Conditional guidance**: board rules (position carries no meaning, ignore edge-clipped content) and raster rules (no page number, may be a fragment, may overlap) render only when such captures are in the batch.
- **One exclusion vocabulary**: both templates render the exclusion classes from the same `taxonomy.excluded` list, with a test asserting they agree — otherwise the auditor would validate against a policy the extractor never received.

Style rules and notation forms are injected from `generated/validators/` and `generated/symbols/` — dual consumption of the compiled artifacts, not a second copy. Telling the extractor the rules reduces validation retries; the regex engine still enforces them independently.

**Invocation (`runner.py`):**

```
cat <staged>/prompt.md | claude -p --output-format json --bare --allowedTools "Read"
```

Images are staged on disk; the prompt lists their absolute paths and instructs reading them. Subprocess timeout 25 min → kill + requeue. Parse the CLI's JSON envelope; extract the final text; parse the **inner contract** (strict: first `{` to last `}`, `json.loads`, then pydantic):

```json
{"batch_id": "...",
 "items": [ {tmp_id, type, form?, slots, title?, topic, terms, figure_refs?} ],
 "fragments": [ {continues: "<ulid>", payload: {…}} ],
 "duplicates": [ {tmp_id_or_new: "...", of: "<ulid>"} ],
 "unclassified": [ {capture_id, region, transcription, note} ],
 "pending_refs": [ {tmp_id, identifier} ],
 "figures": [ {parent: "tmp-id|ulid", capture_id, bbox} ],
 "coverage": [ {capture_id, region, disposition: "items:<tmp-id[,tmp-id...]>|excluded:<reason>|blank"} ],
 "terms": ["…"], "notes": "…"}
```

`capture_id` identifies which staged image a region belongs to (a batch may mix captures, and a raster capture has no page number). `excluded:<reason>` enum = `question | problem | solution | worked-demonstration | recall-repeat | narrative | non-content | foreign-subject` — `source-correction` covers errata and typo notes about a textbook — true, deliberate, and still not mathematics (A28); `narrative` covers connective/meta prose carrying no fact ("We list here…", "as we saw in Sec. 1", assertions of derivability such as "follows easily from the definitions"); `non-content` covers logistics/announcement writing on boards, and any reader annotation over captured content (A24). **`foreign-subject`** covers a fully-visible board belonging to a different course — observed in real material 2026-07-31, where a differential-geometry board shared the frame with a ring-theory lecture. Geometric rules cannot catch this (the board is uncropped and cleanly detected); only the topical test can, which is why the extractor is given its field and lexicon. Pipeline maps `tmp_id`s → fresh ULIDs on acceptance. Failures: schema-invalid inner JSON → ≤2 retries with validator errors appended; then park batch. Rate-limit signatures (envelope error text / exit code) → requeue + halt extraction for the run. **Record/replay:** every call's inputs digest + full envelope → `state/calls/`; `KB_REPLAY=1` makes `runner` serve recorded envelopes, so every stage after extraction is testable offline.

**Headless sources (segmentation and classification rules — mandatory prompt content).** Much textbook material carries no "Definition"/"Theorem" label; classification is always semantic, never label-dependent, under these rules:
1. **Segmentation is the extractor's job**: decompose prose into atomic items — one independently stated fact or one defined term per item; a single paragraph may yield many items (a source region maps to a *list* of tmp-ids in `coverage`); sentences defining several terms at once are untangled into one definition per term; conjoined dual identities keep the source's own display grouping (e.g., both commutative laws = one proposition).
2. **Classification rubric**: content that introduces/names a concept → `definition` (per-source typographic cues from `conventions` apply, e.g. bold-italic terms); a headless asserted result → `proposition` by default (`theorem` is reserved for source-labeled theorems and canonically named major results); local auxiliary asserted facts → `claim`; qualitative/contextual facts → `remark`; genuinely ambiguous → `unclassified`, never force-fit.
3. **Justification routing**: lecturer-invoked *unnamed* standard facts → `by-fact` with the fact inline; `pending-ref` is reserved for explicit identifier citations ("Theorem 2.4", "(2)", "§57"). Operational corollary: ingest a field's textbook before/alongside its boards to shrink the pending-ref wave.
4. **Never synthesize proofs**: a proof object exists only when the source presents an actual argument. "It is clear that", "follows easily from X", "the reader may verify" ⇒ `proofs: []` and the derivability remark is `narrative`. Fabricated rigor is worse than an honest absence.

## I-8. Validation (ordered; each failure names its route)

1. inner-contract pydantic validation → retry loop.
2. STG checks (balanced `$`, legal ref tokens) → retry loop.
3. per-type slot schema → retry loop, then unclassified queue.
4. lexicon: banned→substitute+log; load-bearing unknown → flag + new-term queue; incidental unknown → pass + queue term.
4A. **rule-engine pass on slot content** (your regex engine, rules from `generated/validators/`):
   forbidden words and connectives (Common §14), hyphenation (§13), abbreviation bans (§18),
   display-vs-inline (§19), field notation forms. Deterministic substitution where the rule is a
   pure pair; flag otherwise. This is the stage that catches what frames cannot reach — the
   2026-05-03 slice produced "harmonic conjugate of $u$ on $D$" (CA §6) and "…, so $u$ is not…"
   (Common §14), both inside slots, both invisible to the renderer.
5. symbols lint → same pattern.
6. completeness per type → incomplete ⇒ `status: open` (not an error). An **empty `proofs[]` is not incompleteness** (I-3); `open` means a *started but unfinished* structure — a proof missing its conclusion, a declared-but-absent case.
7. dedup pass (I-4) → merges / near-duplicate queue.
8. ref integrity: every `{ref:…}` token resolves to a store item, else the pending-ref queue. A ref inside a *statement* slot flags the item. A ref inside a *proof* also flags the item — an unresolved ref must never be rendered as vague prose. Note the interaction with A20: a ref that resolves but whose target is not in the current build is not an error; the renderer simply omits that justification (I-11).
9. per-item Typst compile smoke: item emitted standalone with template + symbols → `typst compile`; failure → flagged with compiler output attached (catches dialect/escaping bugs before book builds).

## I-9. Coverage audit

Per batch, second `claude -p` call: page images + accepted item summaries + the excluded-classes block + the batch's `coverage` declarations. Contract:

```json
{"gaps": [{capture_id, region, description}],
 "exclusion_violations": [{capture_id, region, reason}]}
```

Part 1: facts present in source, absent from items. Part 2: **validate every `excluded` region against the written policy** — a region skipped as e.g. `worked-demonstration` that actually establishes a qualifying fact (a real counterexample) is a violation. Exclusions are audited, never trusted. Both arrays empty = pass; otherwise one targeted re-extraction of the named regions, then audit-gap queue. Same-model blind-spot caveat stands (B9); `knowledge-base spotcheck` samples N random items/week and shows you item vs source region.

## I-10. Queues and CLI surface

Queue file: `queue/<name>/<id>.yaml` with `{kind, created, payload, context_paths[]}`. Queues: new-term · near-duplicate · unclassified · open-gone-quiet · figure-crop · new-source · **unsorted-source** (A25) · **low-resolution** (I-6.3c) · pending-ref · audit-gap · relint-ambiguous.

| Command | Behavior |
|---|---|
| `knowledge-base run` | full pipeline once (manual nightly) |
| `knowledge-base sync / ingest / extract / validate / audit / build` | individual stages |
| `knowledge-base review` | Rich UI, one decision/screen, all queues; writes profile+store+`decisions.log` |
| `kb browse [field]` | read store; star toggle; open source image of any item |
| `kb star <id> [--off]` | manual override of derived star |
| `kb edit <id>` | open item YAML in `$EDITOR`, then revalidate + recompile-smoke + commit |
| `knowledge-base relint` | retroactive lexicon enforcement (I-5) |
| `knowledge-base rules` | recompile `rules/` → `generated/` (same as `make rules`); fails if generated artifacts would change without a rules edit |
| `kb spotcheck [n]` | random item-vs-source verification session |
| `knowledge-base status` | budget state, queue counts, open items, last run report |

Every ruling appends to `decisions.log` (append-only): the human-judgment layer is auditable and replayable.

## I-11. Build

**Frames (`generated/frames.py`)** — the consistency core, now **compiled from Proof Style + Common** (I-5A) rather than authored here. All connective language comes from it and nowhere else; editing a rule document and recompiling restyles the entire corpus retroactively. Implemented and verified in `frames_v1.py` (kb-rulecompliant-artifacts.zip). Key behaviors:

- **Transitions** (§3.2, A17): selected from `justification.kind` — named fact applied → "Therefore"; pure algebra or computation → "Then" (A22); mechanical operation → "This gives"; explicit `transition` slot carries "Note that" / "Similarly" / "Moreover".
- **Justification placement** (§2): terminal (`[Statement], by the [Name].`); `Since [reason], [statement].` is the only initial form.
- **Citation resolution** (A16): target's name if it has one, else its `citation_form`. Never a number. Composing a citation from hypotheses+conclusion is a fallback that indicates a schema violation.
- **Presence computed at build time** (A20): a fact in the document is justified on first use; a fact absent from the document gets **no** justification; an identical justification in the immediately preceding step is omitted. Consequence to expect: proofs gain justifications automatically as the corpus grows — in the slice, every Cauchy–Riemann justification is currently suppressed and will reappear in named form once that theorem is ingested.
- **Openings** (A18): imperative, no "we" — "Consider $k$ cases.", "Proceed by induction on $n$.", "Prove the contrapositive.", "Construct [object] explicitly."; the biconditional opener is deleted since the arrows carry the structure. Direct proofs derive "Assume that [hypotheses]." from the parent statement (§4.1).
- **Arrows** (A19, compiler-verified): `$(=>)$` / `$(arrow.l.double)$` → ⇒ / ⇐. `$<=$` renders as ≤ and must never be used as an arrow.
- **Closings** (§3.3): "Hence …" / "In all cases, …" / "By induction, … for all $n in NN$."

- **Statement forms** live in Common §21 and compile the same way: definition noun form (with `article`, including the no-article case), definition predicate form, the `Let [context]. ` prefix, theorem-class `Assume that [hypotheses]. Then [conclusion].`, and the two counterexample frames.

*(The v0 frame wording authored before the rule documents arrived has been deleted from this plan rather than archived in it. It contradicted the live specification above on three counts — hypothesis wording, the contrapositive opening, and numbered cross-references — and anyone implementing from it would have reintroduced all three. The historical record lives in kb-slice-artifacts.zip, outside the specification.)*

**numbering_sim.py:** walks the emission order; level-1 heading ⇒ section += 1, counter = 0; each numbered item ⇒ counter += 1, number `sec.n`, label `<key>-<sec>.<n>` per template keys; `unnumbered_advances = false`, resolved empirically against the real template (B5). **Parity method:** compile the torture doc, then `typst query` all `figure.where(kind: "math-env")` elements and compare the full label set + numbering against the simulation — exact set equality is the test.

**emitter.py:** deterministic store → `.typ`: imports, `#show: project.with(title, authors, date: none)`, `symbols-gen.typ`, chapter headings from outline, per item the mapped template call with frame-rendered body; `{ref:ulid}` → `@<label>` via the sim; display math as block `$ … $`; figures as `#figure(image("assets/…"))` under the parent; star flag per derived/override value. **Escaping:** prose runs escape `\ # $ [ ] { } @ * _ ` + backtick + `< > ~` and `//`; property test: adversarial random strings in a remark body must compile. Byte-identical output for identical store state (golden-file tested).

**star.patch spec (as built, 2026-07-20):** `star: false` is threaded through the tier wrappers into `math-item` / `math-item-unnumbered`, which publish it via `state("math-env-star")`; the figure show-rule reads that state at the element's own location and passes it to `thm-box` / `semi-box` / `light-box`, prefixing `★ ` in the Tier-1/2 badge and before the name in Tier-3. The state channel is necessary because the show-rule boundary accepts no parameters. 152-line diff (the original ~10-line estimate missed this); behavior is byte-identical when the flag is unset. Verified visually and by `typst query` in S3.

**Dialect (B13):** slots carry math in one dialect, fixed in config after S1's A/B measurement. Path A (default preference): Typst math directly — zero conversion layer; requires acceptable model fluency. Path B: LaTeX in slots + deterministic conversion at emission (pinned converter dependency); fallback if A's error rate is material. The compile-smoke step is the per-item guard either way.

**compile/publish:** vendored `typst compile --font-path fonts/`; PDFs + `report.md` → Drive Output.

## I-12. Orchestration

`bin/nightly.sh` → `python -m kb.ops.nightly`: stages `sync → ingest → extract → validate → audit → commit → build → publish → report`, each idempotent; `flock` lockfile; per-stage state in `state/progress.json`; extraction loop honors `max_pages_per_night` and halts cleanly on limit events (requeue, resume next run). Failure policy: any stage error ⇒ commit completed work, write report with the error, exit nonzero. `report.md`: pages processed per field, items added/merged, open-item count, queue deltas, audit results, limit events, durations.

**Scheduling:** Windows Task Scheduler daily 21:30 → `wsl.exe -d Ubuntu -- /home/<user>/kb/bin/nightly.sh`; task set to run only when a user session exists (machine is on evenings), wake-capable, no battery restriction. **[B14]** Session-less/headless `wsl.exe` invocation from Task Scheduler has known environment quirks (user context, appended PATH, WSL VM cold start); verified during Phase 4 first setup; fallback = logon-triggered + on-idle task, functionally equivalent for your usage pattern.

---

# PART II — BUILD SEQUENCE

Conventions: WP = work package ≈ one focused Claude Code session (or less). Every WP ends with `make check` green and a commit. Steps are ordered; tests named per WP; each phase ends with an explicit gate you accept.

## Phase 0 — Foundations and spikes

**WP0.1 Bootstrap.** Steps: repo init per I-2 skeleton; `uv` project + closed dep list; Makefile (`check`, `run`, `bootstrap`); bootstrap script fetching typst + fonts with sha verification into `tools/`/`fonts/`; gitignore + pre-commit hook; `config.py` + example `config.yaml`; logging setup. Tests: config round-trip; bootstrap idempotency. DoD: fresh clone + `make bootstrap check` green.

**WP0.2 S3 — template mechanics. ✅ EXECUTED 2026-07-20 in-sandbox** (artifacts: kb-s3-artifacts.zip; the results are recorded in docs/FINDINGS.md, "Toolchain and numbering"). All steps below are DONE and their outputs are in the archive; on desktop this WP reduces to porting them into the repo and re-running the parity test against the pinned typst as a regression check. Steps (completed): author `star.patch` per I-11 and apply to vendored copy; hand-write `tests/fixtures/torture.typ` (all emitted envs interleaved with unnumbered ones, 3 chapters, cross-chapter `@`-refs, starred items, page-breaking boxes, adversarial escaping strings); implement `numbering_sim.py`; implement `compile.py` incl. a `typst query` wrapper; parity test comparing sim label set vs queried label set. Resolves **B5** (sets `unnumbered_advances`). DoD: parity test green; you eyeball the torture PDF once (star rendering, box behavior).

**WP0.3 S1 — extraction probe.** Steps: staging script (drop sample set from Drive → staged batches, both raw and quad-cropped variants); prompt v0 (subset taxonomy: definition/theorem/proof + coverage + duplicates + fragments), in **two dialect variants** (Typst math / LaTeX math); minimal `runner.py`; scorecard doc with per-page fidelity/classification/coverage columns plus headless segmentation/classification columns (golden fixtures now also include four sessions chosen from the real corpus — LA 2026-03-03 at 21 photographs, the LA 2026-04-07 five-lecture upload batch, AA 2026-03-23, and the AA 03-11/03-16 pair; see docs/FINDINGS.md, "Session grouping and volume". Plus the two headless textbook samples, which are themselves **textbook × raster** captures; the board set has photographs but **no worked expected item set** — producing one is part of WP0.3, not an input to it; the raster fixtures also calibrate the B16 resolution floor); run: textbook pages ×2 dialects, board crops ×2 dialects, raster captures ×2 dialects, the split-proof sequence, the rewritten-content pair; EXIF dump check across the Drive path (including whether screenshots carry camera tags, which is what `route.py` keys on); quad-detection prototype over all board photos; text-height measurement across every capture to set `resolution_floor_px`. Resolves **B1 B2 B10 B11 B13 B16**, first evidence **B12** (none exists yet); triggers **A10** or not. DoD: scorecard filled; `dialect` set in config; go/no-go note per exit criteria (≥95% textbook items usable untouched; boards scored separately; continuation + duplication behaviors observed).

**WP0.4 S2 — budget.** Steps: instrument runner timing + limit events during WP0.3; extrapolate sustainable pages/night vs your interactive headroom; set `max_pages_per_night`. Resolves **B3** magnitude; triggers **A11** or not.

**Phase 0 gate:** you review scorecard + torture PDF + budget note; conditionals A10/A11 decided if triggered.

## Phase 1 — Core loop (textbook PDFs, Complex Analysis, def/thm/proof)

**WP1.1 Models + store.** `models/` per I-3 (incl. proof substructures, counterexample — defined now even if unused until Phase 2); JSON Schema generation; `store.py` (atomic temp+rename writes, load/index, git commit helper); ULID assignment. Tests: schema round-trips; store atomicity; canonical JSON-Schema snapshot.

**WP1.2 Textbook ingest — PDF *and* raster.** `route.py` (kind from folder, capture from file), `pdfdoc.py`, `raster.py` (pass-through), `resolution.py` (gate + `low-resolution` queue), `registry.py`, `groups.py`, source registration (ToC-proposal stub → new-source queue; `_unsorted` → unsorted-source queue per A25). Raster belongs in Phase 1, not Phase 3: screenshots are textbook-kind input and are a primary capture route, not a board variant. Tests: fixture PDF → renders/text/images; screenshot fixture → untouched pass-through; resolution gate on a downscaled fixture; hash idempotency; group assignment independent of filename and mtime.

**WP1.3 Prompt v1 + runner hardening + replay.** ✅ **Prompt packs built and tested 2026-07-30** (kb-prompt-packs.zip) — port them in, then narrow the taxonomy to Phase-1 types by config rather than by editing the templates. Full inner contract (I-7); `prompts.py` (Jinja pack assembly, `prompt_hash`); retry-with-errors loop; limit detection; `state/calls/` recording + `KB_REPLAY`. Tests: envelope/inner parsing incl. malformed cases; replay determinism.

**WP1.4 Validation v1.** Checks 1–3, 6, 9 of I-8 (lexicon starts empty; dedup Phase 2); `open` status wiring. Tests: each check's failure route; compile-smoke on fixture items.

**WP1.4A Rule compilation.** Parse `rules/` → `generated/lexicon/`, `generated/symbols/`, `generated/validators/`; wire your regex engine to consume the generated validator rules; `make rules` regenerates and `make check` fails if generated artifacts are stale relative to the documents. Tests: golden compilation of a 20-rule fixture; staleness detection. DoD: CA lexicon and symbol registry generated from `Complex Analysis.txt` with a manual spot-check of 20 entries.

**WP1.5 Frames + emitter + build.** `frames.py` compiled per I-5A (start from the verified `frames_v1.py`); `emitter.py` with escaping + sim integration; `symbols-gen`; outline loader; `kb build`. Tests: golden `.typ` from a fixture store (byte-exact); escaping property test; end-to-end replay test: recorded S1 envelopes → store → build → compiled PDF.
→ **First real milestone:** ingest CA textbook chapter 1 live; produce the ToC-derived outline for your one-time approval (A5 flow); build the first PDF.

**WP1.6 Proof pilot (B7).** Extract 20 real proofs across chapter variety; score distortion item-by-item with you; extend proof schema where needed (A7: extend-only). DoD: distortion verdict recorded; schema v1 frozen or extended.

**WP1.7 Lexicon seeding.** Term-proposer report from all chapter-1 output → one sitting of canonical rulings with a minimal `knowledge-base review` (new-term queue only); `relint` first run. DoD: chapter 1 rebuilt with zero unknown load-bearing terms.

**Phase 1 gate:** you read the chapter-1 PDF end-to-end and accept every item (or file the deltas as rulings/schema extensions).

## Phase 2 — Full validation, dedup, review

**WP2.1 Canonical + dedup.** `canonical.py`, `dedup.py` per I-4 (incl. subset match, keep-both-proofs). Tests: normalization determinism; threshold behavior on constructed near-pairs.
**WP2.2 Queues + full review CLI.** All queues of I-10; `decisions.log`; `knowledge-base edit`, `knowledge-base status`. Tests: queue IO; decision replay.
**WP2.3 All types + relint.** Remaining Phase-scope types (corollary, axiom, claim, counterexample, notation, remark) in prompts/frames/emitter; `knowledge-base relint` full implementation. Tests: counterexample frame rendering; relint auto vs ambiguous routing.
**WP2.4 Overlap trial.** Ingest a **second Complex Analysis source** covering chapter-1 material; verify merges, star inheritance, precedence suggestions, zero silent synonym leaks; tune thresholds (B6).
**Phase 2 gate:** overlap trial report accepted.

## Phase 3 — Boards

**Prerequisite, and the only one not already satisfied.** The configured fields are
Complex Analysis and Ordinary Differential Equations. The material in Drive is a
Complex Analysis textbook PDF plus roughly 200 board photographs of Linear Algebra
and Abstract Algebra, which are not configured fields. Phases 0–2 are
textbook-driven and run on the PDF that exists; this phase is board-driven and, as
configured, has nothing to ingest. Resolving it is a one-line config change plus a
field rule document per subject — flagged rather than decided, because which books
get built is the owner's call, and building one he did not ask for is the expensive
error. Report at the start of this phase; do not stop earlier for it.

**WP3.1 Photo chain production.** `photo.py` per I-6.3a with fallback flag; board-group assignment in `groups.py` (the module itself ships in WP1.2). Tests: quad detection on the S1 photo set (recorded expectations); EXIF-gap grouping on synthetic sets.
**WP3.2 Continuation.** Open-set state, fragment merge + revalidate, cross-session carryover, open-gone-quiet queueing. Tests: replay of the S1 split-proof sequence end-to-end.
**WP3.3 Figures.** bbox crop + padding, PDF embedded-image path, figure-crop review gate, emitter embedding. Tests: fixture figure flow.
**WP3.4 Audit stage.** `audit.py` per I-9 incl. exclusion validation + targeted re-extraction; `knowledge-base spotcheck`.
**WP3.5 Live lecture week.** Run a real week of CA lectures through `knowledge-base run` daily; evaluate B12 (continuation, repeat collapse, worked-demonstration skipping), figure gating, board fidelity in production.
**Phase 3 gate:** live-week report accepted; A4 relaxation decided or kept.

## Phase 4 — Automation

**WP4.1 Nightly driver.** `ops/nightly.py` stage machine, lock, state, budget guard, report. Tests: stage idempotency; simulated limit-event resume; kill-mid-run resume drill.
**WP4.2 Sync + publish.** rclone in/out per I-6/I-11; new-file detection loop.
**WP4.3 Scheduler.** Task Scheduler task per I-12; resolve **B14** (fallback trigger if needed); one supervised scheduled run, then one unsupervised.
**Phase 4 gate:** one full week, zero manual pipeline actions; your touches = review minutes only.

## Phase 5 — Second-field onboarding (ODE)

**WP5.1 Onboarding runbook.** Written checklist distilled from doing it: profile authoring order, seed lexicon strategy, calibration batch size, expected flag density. (This runbook is itself a deliverable — it is what "one-time setup per subject" concretely means forever after.)
**WP5.2 ODE profile + calibration.** Author `fields/ode/profile/`; run a calibration batch; ruling sitting; reach Phase-3 capability changing only profile files.
**Phase 5 gate:** ODE book building nightly; any core-code change required during WP5.2 is treated as a defect and fixed in core.

---

# PART III — REGISTERS AND CHECKLIST

## III-1. Decisions

**Open:**

| # | Decision |
|---|---|
*(Both entries below have pre-recorded defaults in `DECISIONS-TAKEN.md` and must not block an unattended run — they are for the owner's later review, not for asking about.)*

| A10 | *Conditional* — only if S1 fails on board fidelity: review-gate all board items |
| A11 | *Conditional* — only if S2 shows a throughput shortfall: choose the trade-off |

**The register is closed.** No unconditional decision remains open. A10 and A11 fire only if a Phase 0 measurement demands them, and both carry conservative defaults recorded in `DECISIONS-TAKEN.md`.

**Resolved 2026-07-31 (from reading twenty real board photographs, docs/FINDINGS.md):** new exclusion class `foreign-subject` for fully-visible boards belonging to another course — geometric rules cannot catch these · taxonomy label aliasing (Defn/Definition, Prop/Proposition, Thm/Theorem, Pf/Proof, ex/Example) · **A27** exercises that assert facts contribute the statement as a proposition with empty `proofs[]`, question framing dropped — decided by precedent from A14 rather than left open, veto if wrong · coloured chalk carries lecturer emphasis but is ignored in v1.

**Resolved 2026-08-02:** A26 session identity — the I-6.5 precedence, resolved once at first ingestion and persisted in the registry so later runs never re-derive it; dated subfolders supported but not required.

**Resolved 2026-08-01:** A27 colour carries no meaning in v1 — coloured content is extracted exactly as white, with no special routing and no colour-based exclusion; the in-place correction rule is independent of colour and stands · A28 source corrections excluded entirely — no `source-note` type; errata about a textbook are `source-correction` in the exclusion enum.

**Resolved 2026-07-29 (third input path):** A25 `books/<source-key>/` subfolders with the `_unsorted` fallback, one queue entry per drop, items flagged until sourced · A23 folder convention `Lecture-Boards/` + `Texts/`, format-agnostic, supplying `kind` deterministically — supersedes A8's "photos at root" · A24 raster captures never contain personal annotation; no annotation handling is built, and any annotation that does appear falls to the existing `non-content` exclusion class, requiring no new machinery · filenames carry no convention across devices and are never parsed for ordering, grouping, or source identity.

**Resolved 2026-07-28 (rule-document integration):** A15 non-enum counterexamples enter as claim + constructive proof · A16 citations resolve to name, else `citation_form`; never a number · A17 Proof Style §3.2 six-way transitions win; Common §15.2 deleted · A18 "we" removed entirely, openings imperative · A19 `$(=>)$` / `$(arrow.l.double)$`, compiler-verified · A20 justification presence computed at build time from store membership · A21 `citation_form` always populated · A22 "Then" for pure algebra and computation steps.

**Resolved 2026-07-20:** A13 Drive + local mirror confirmed as the permanent archive · A14 proof content inside exercise/example apparatus in scope, question framing excluded.

**Resolved earlier (unchanged):** A1 star patch · A2 two books · A3 no automatic content precedence, star inherited via provenance · A4 figure review-gate · A5 ToC outline approved once · A6 star derived from board provenance, `knowledge-base star` override · A7 extend-schema-only · ~~A8 Drive convention~~ *(superseded by A23)* · A9 equations never numbered, refs only in proofs, example/question/problem/solution removed, template functions left in place · A12 remark/notation kept, recall extraction-unreachable, counterexample schema-gated via `#claim`, worked demonstrations excluded · Fonts vendored from official repos.

**Decided in rev 4 under delegated judgment (flagging, not asking):** math-dialect choice made empirically in S1 (B13) with Typst-native as default preference · `non-content` board exclusion class (logistics/announcements) · definition `form` variants (noun/predicate) with two fixed frames · proof substructures for induction/cases/uniqueness · retroactive lexicon enforcement via `knowledge-base relint` · within-topic ordering key (textbook page order, board-only items after, `order` override) · per-batch extractor/prompt provenance recording · frames centrally editable ⇒ retroactive restyle · `rapidfuzz` added to the dep list · headless-source rules (segmentation, classification rubric, proposition-default, never-synthesize-proofs) · `narrative` exclusion class · per-source `conventions` profile · definition `article` slot · proofless-statement policy (empty `proofs[]` valid, tracked, merge-completed) · identifier table generalized to equation/section refs · multi-item coverage disposition · `iff-pair` proof method *(invented, not observed — no empirical provenance)* · `article: none` · by-fact vs pending-ref routing rule *(invented, not observed)* · textbook-first ingestion recommendation · frames and emitter promoted to tested code, exercised on synthetic input only.

## III-2. Uncertainties

| # | Uncertainty | Resolution |
|---|---|---|
| B1 | ~~Board-photo extraction fidelity~~ **Resolved 2026-08-01**: every symbol readable in nineteen of twenty real captures, including subscripts, superscripts, 3×3 matrix entries, integral bounds and quotient notation. One soft-focus frame sits at the margin and sets the practical resolution floor | Done; runtime-model fidelity still measured in WP0.3 |
| B2 | Headless `-p` behavior parity: vision input, Read auto-approval, envelope field stability | WP0.3 |
| B3 | Pro limits alongside interactive use. **Volume measured 2026-07-31**: two real subjects produce ~38 photographs/week, so four subjects project to ~76 — the 200/week planning figure is ~2.6x conservative. The open question is cost per capture, not capture count. Bursts are the real load: one upload delivered 46 photographs at once | WP0.4 |
| B4 | No programmatic remaining-quota check → adaptive stop/resume only | Accepted |
| B5 | ~~Unnumbered envs and the shared counter~~ **Resolved 2026-07-20, in-sandbox probe against the real template (typst 0.15.1):** unnumbered envs do **not** advance the counter (thm-1.1 → remark → thm-1.2 → notation → def-1.3; section reset to lem-2.1 verified; unnumbered envs carry no label; `@`-refs resolve). `unnumbered_advances = false`. | Done; WP0.2 re-verifies on the pinned version |
| B6 | Near-duplicate thresholds; equivalence permanently human-final | WP2.4 tuning |
| B7 | ~~Proof step-grammar expressiveness~~ **Partially resolved 2026-08-01** on twenty real board captures: the *step* grammar handled every observed proof; the *method* enum did not. `double-inclusion` and `verify-criteria` added, plus a `sufficiency` setup form. Residual risk is that further methods surface — the extend-only policy (A7) absorbs them | WP1.6 pilot for textbook proofs |
| B8 | Figure bbox precision | Phase 3 + review gate |
| B9 | Same-model audit blind spots | spotcheck; future cross-model |
| B10 | EXIF survival through capture→Drive→rclone | WP0.3 |
| B11 | Board-quad detection robustness | WP0.3 |
| B12 | Continuation + duplication on real lecture flow — **no evidence yet**; the 2026-07-20 evidence was withdrawn as synthetic | WP0.3 first evidence; WP3.5 evaluation |
| B13 | Model math-dialect fluency (Typst-native vs LaTeX+conversion) | WP0.3 A/B; config `dialect` |
| B14 | Task Scheduler → headless WSL invocation reliability | WP4.3; logon/on-idle fallback |
| B17 | Prompt-pack instruction-following: schema adherence, coverage completeness, whether the proposition-vs-theorem default misfires, and true pack cost against the live model. The packs are verified for *renderability and internal consistency* only — they have never been sent to the runtime model | WP0.3 first real batch; expect one revision |
| B16 | Resolution floor below which a capture cannot be trusted to preserve subscripts, primes, and integral bounds | Measured in WP0.3 on your real screenshots and board photos; sets `resolution_floor_px` |
| B15 | `citation_form` is the one slot that is **restatement, not transcription** — the sole point where LLM-authored prose enters the rendered book. Consistency is preserved (authored once per item, then reused identically at every citation site), but quality is not guaranteed | Review-gate `citation_form` on item creation in `knowledge-base review`; measure agreement on the WP1.6 proof pilot |

Posture unchanged: rendering-side consistency 100% by construction; extraction-side fidelity rare-detectable-recoverable. B1, B3, B7, B12 remain the four possible scope-conversation points, all closed by end of Phase 3.

## III-3. Your checklist

1. Review the 2026-07-29 rule-document edits (kb-rules-edited.zip / CHANGELOG.md) and accept or amend them. They are now the compilation input for `generated/`, so an unreviewed edit propagates into every rendered sentence.
2. ✅ **Done 2026-07-20:** Phase-0 sample set delivered — 10 board photos including the split proof and a "Last Time" review board, two raster textbook captures, and the full Brown & Churchill PDF. On desktop, re-file them into the A23 layout (`boards/` and `books/<source-key>/`).
3. **Before Phase 2:** provide a **second Complex Analysis source** (PDF) overlapping chapter-1 material — required for the WP2.4 overlap trial. Still outstanding.
4. Once desktop access returns: WSL Claude Code login; rclone install + Drive OAuth; confirm `wsl.exe -d <distro>` fires from Task Scheduler.
