# Decisions taken

The record of why each non-obvious decision in this project was made. Append one
entry per decision; never edit or delete an existing entry. Newest last.

Entries dated 2026-08-04 and 2026-08-14 were made under an autonomous-operation
protocol that has since been removed (plan revision 17). They are kept because the
reasoning is sound and several of them record defects that cost real time to find.
Read them as history, not as precedent for deciding without asking.

From revision 17 onward, decisions are made with the owner before implementation,
and the entry records the decision that was agreed.

Format:

<date> · <short title>

Context   : what forced a choice
Chosen    : what was decided
Authority : rule document § / plan § / owner decision
Reversal  : cheap | moderate | expensive — and what undoing it would touch

---

## Pre-recorded defaults — apply these without logging

These are already decided. Applying them is not a decision and needs no entry.

- **A26 session identity** — settled policy, not a default: the plan §I-6.5
  precedence, resolved once at first ingestion and persisted in the registry.
  Never re-derive a session for a capture already ingested.
- **A25 unsourced captures** — ingest normally, hold `source` null, raise one
  `unsorted-source` queue entry per drop, keep the items flagged until answered.
- **A10 / A11** — do not trigger unless the Phase 0 measurement demands it. If it
  does, take the conservative branch (review-gate board items; reduce nightly
  throughput) and log it.
- **Anything else in the plan's decision register marked resolved** — it is
  resolved. Do not re-open it.

---

# Entries

## 2026-08-04 · Archive unpacked to the repository root, not to a subdirectory
Context   : `knowledge-base-pipeline.zip` contained a single top-level directory.
            Extracting it verbatim would have put the project one level down, so
            `CLAUDE.md` and `docs/` would not be where every document says they are.
Chosen    : Stripped the wrapper directory; contents now sit at the repository
            root, matching the layout in plan §I-2 and every path in the docs.
Authority : fallback ordering rule 2 (the plan settles it — §I-2 shows these paths
            at the root)
Reversal  : cheap — a `git mv` of the whole tree.

## 2026-08-04 · `make check` and `make bootstrap` run through `uv` when present
Context   : Both commands assumed the project's dependencies were importable by
            the bare `python3`/`pytest` on PATH. On a fresh clone that is false
            (`ModuleNotFoundError: jinja2`), so the README's getting-started block
            was broken in the same way revision 16 had already fixed once.
Chosen    : The Makefile detects `uv` and runs `uv run --extra dev …`; without uv
            it falls back to the previous bare invocation unchanged. `uv.lock` is
            now tracked, per plan §I-1 ("uv for env + lockfile").
Authority : fallback ordering rule 2 (§I-1 names uv as the environment manager)
Reversal  : cheap — four lines of the Makefile.

## 2026-08-04 · `config.yaml` is loaded by a strict model that rejects unknown keys
Context   : `config.py` was unwritten and the plan does not say how tolerant it
            should be.
Chosen    : `extra="forbid"` and frozen models. A key nobody reads is
            indistinguishable from a key that was silently misspelled, and the two
            measured values (`budget.max_pages_per_night`, `resolution_floor_px`)
            stay at 0, which every consumer reads as *unmeasured* rather than as a
            plausible default.
Authority : fallback ordering rule 4 (preserve information — a typo must surface,
            not vanish) · UNFORESEEN as to strictness specifically
Reversal  : cheap — one `ConfigDict` line.

## 2026-08-04 · The pre-commit guard enforces `generated/` by recompiling it
Context   : The hard rule is "never hand-edit `generated/`", but `generated/` is
            tracked, so a diff there is not by itself evidence of hand-editing.
Chosen    : The hook rejects any staged path under `build/`, and for staged paths
            under `generated/` it re-runs the rule compiler in `--check` mode and
            fails if the committed bytes differ from what `rules/` produces. This
            is the same test `knowledge-base rules` performs (§I-10). The check
            skips with a warning while the compiler is unbuilt.
Authority : plan §I-1 (hook spec) + §I-10 (`rules` fails on staleness)
Reversal  : cheap — `bin/pre-commit` is a tracked shell script.

## 2026-08-04 · Lexicon extraction restricted to two stated shapes; the rest are proposals
Context   : Plan §I-5A says the ALWAYS/NEVER lines "parse straight to
            `banned: {Y: X}`". Executed against the real documents, a
            nearest-preceding-ALWAYS parser produced confidently wrong rulings:
            `domain -> region` (CA §17.1, whose sentences say the opposite),
            `function -> an entire function` (§5.1, where the second quoted word
            explains the prohibition), `infinity -> the` (§17.1),
            `counterclockwise direction -> negatively oriented` (§7.2, paired
            with the wrong one of two mandates). Each would have become an
            automatic corpus-wide rewrite.
Chosen    : Two confidence tiers, both requiring the author to have stated the
            association — a sentence tier (em dash inside one sentence) and a
            paragraph tier (exactly one ALWAYS clause, first NEVER not
            re-quoting the mandated term). Plus two guards: a substitution that
            would rewrite its own replacement, or corrupt a mandated proper
            name, is refused. Everything else goes to
            `generated/lexicon/<field>.candidates.yaml` with its source
            sentence — 61 proposals for CA, none enforced.
Authority : fallback ordering rule 4 (preserve information — never force-fit)
            and rule 3 (reversible) · a measurement contradicting a plan claim,
            reported here rather than stopped on, since it changes *how* the
            compiler works and not *whether* the run can continue
Reversal  : cheap — widening the tiers is a change to `rules/parse.py`, and the
            candidates file already holds everything the stricter rule declined.

## 2026-08-04 · Proof_Style.txt compiles to none of the three mechanical targets
Context   : §I-5A's table assigns Proof Style to Frames, but its rulings are
            written in the same ALWAYS/NEVER shape as terminology, so a naive
            compiler ingests them. "ALWAYS use `Hence` for the final concluding
            sentence. NEVER use `Therefore` … as the final closing sentence."
            compiled to a store-wide substitution of Therefore -> Hence.
Chosen    : Destination is enforced per document. Proof Style reaches the system
            only through hand-written frames and the conformance test.
Authority : plan §I-5A (destination decides, not topic)
Reversal  : cheap — one table in `compile_rules.py`.

## 2026-08-04 · The emitter writes no `<label>`; the template attaches it
Context   : Compiling a real document failed with "label `<prop-1.3>` occurs
            multiple times". `math-item` in `template-star.typ` already attaches
            a label from the same key-and-counter scheme `numbering_sim` models.
Chosen    : The emitter emits the call and lets the template label it, matching
            the verified WP0.2 torture fixture. Titles are emitted as content
            blocks for the same reason — that is what the verified fixture does.
Authority : fallback ordering rule 1/2 · the verified artefact is the reference
Reversal  : cheap.

## 2026-08-04 · Escaping runs on slot text, before frames compose
Context   : Escaping frame output stripped the bold markers Common §21.1 and
            Proof Style §4.3 mandate (`*term*`, `*Case 1:*`, `*(i)*`).
Chosen    : Escape transcribed slot text — the only text a model produced — and
            emit frame output verbatim. Reference tokens resolve in the same
            pass so `@label` survives.
Authority : UNFORESEEN; resolved by the invariant that frames own every rendered
            sentence and slot text is the untrusted half
Reversal  : cheap.

## 2026-08-04 · Frames for `verify-criteria` reuse mandated forms only
Context   : The method was added to the schema on 2026-08-01 from observed
            material. Proof Style §4 has no entry for it, so its frame text is
            unspecified.
Chosen    : An imperative opening in the §4 pattern ("Verify each condition of
            [definition].") plus §4.8's mandated (i)/(ii)/(iii) labels and
            §3.3's "Hence". No new connective language was invented.
Authority : UNDOCUMENTED-DEFAULT — the narrowest option that renders, composed
            from forms the documents already mandate
Reversal  : cheap — one entry in `OPENING`, and the conformance test pins the
            parts that are mandated.

## 2026-08-04 · `by the [Name]`, with a possessive carve-out
Context   : `frames_v1.py` emitted `by {name}`, but Proof Style §2.1 mandates
            `by the [Name]`. Applying it blindly gives "by the Liouville's
            Theorem".
Chosen    : Prefix "the" unless the first word is a possessive — the same test
            Common §21.1 already defines for definition articles.
Authority : rules win (fallback ordering rule 1) · reuse of an existing test
            rather than a new one
Reversal  : cheap.

## 2026-08-04 · An unmeasured budget limits a run to one batch
Context   : `budget.max_pages_per_night` is 0 until WP0.4 measures it, and the
            nightly driver has to interpret that.
Chosen    : 0 means "no budget established", not "unlimited": one batch per
            run. Enough to make progress and to produce the timing evidence the
            measurement needs; far too little to exhaust the subscription
            overnight.
Authority : fallback ordering rule 3 (reversible) and rule 5 (narrower scope) ·
            B3 is explicitly unmeasured
Reversal  : cheap — set the value in `config.yaml` after WP0.4.

## 2026-08-04 · Subset dedup matches on tokens, not substrings
Context   : §I-4's subset rule says the new statement is "contained in" an
            existing one. The normalised statement concatenates conclusion and
            hypotheses, so a review repeat's hypotheses sit after the fuller
            item's extra words and the two never form a contiguous run.
Chosen    : Token containment with a five-token floor. Below the floor,
            near-duplicate review decides.
Authority : fallback ordering rule 2 (the plan's intent — "statement-only
            restatement of a fuller item") · UNFORESEEN as to mechanism
Reversal  : cheap — one function in `dedup.py`.

## 2026-08-04 · A duplicate proposal naming an absent item is queued, not dropped
Context   : The extractor may propose a duplicate of a ULID this field does not
            hold — a stale id, or a target of another type.
Chosen    : Queue it as a near-duplicate. A discarded proposal is the one signal
            nothing downstream can recover.
Authority : fallback ordering rule 4 (preserve information)
Reversal  : cheap.

## 2026-08-04 · Board-quad clipping is screened on the bounding rectangle
Context   : A board running off the frame often approximates to five or six
            points, or to a self-intersecting outline whose `contourArea` is
            near zero, so a polygon-based screen reported *zero* clipped regions
            for a frame full of them.
Chosen    : Screen on the bounding rectangle. The consequence is that a board
            filling the frame now falls back to the whole image with a flag
            rather than being cropped — the conservative direction.
Authority : fallback ordering rule 4 · a diagnostic that under-reports in
            exactly its own case is worse than none
Reversal  : cheap — constants and one branch in `photo.py`.

## 2026-08-04 · `store.commit()` degrades outside a git work tree
Context   : The nightly `commit` stage aborted the whole run when the root was
            not a git repository, discarding the run's extracted work.
Chosen    : Log and continue. Committing makes the store reviewable; it is not
            what makes it correct.
Authority : fallback ordering rule 4 · plan §I-12's failure policy is "commit
            what is done", which a failing commit stage cannot honour by failing
Reversal  : cheap.

## 2026-08-04 · Generated fixtures are used for plumbing tests, and labelled
Context   : No captures are reachable from a cloud session, but routing, EXIF
            parsing, the resolution gate's arithmetic, the PDF chain and the
            quad geometry all need exercising.
Chosen    : `tests/fixtures/make_captures.py` generates PDFs, screenshots and
            JPEGs with hand-built EXIF, and the photo tests draw quadrilaterals.
            Every such file carries a header stating it tests code and is never
            evidence about extraction fidelity, and the tests that would need
            real material (B1, B11, B12, B16) are left unwritten rather than
            faked.
Authority : CLAUDE.md — "drive it with tests rather than with real material" and
            "do not simulate captures to keep going"
Reversal  : n/a — the fixtures are test-only and touch nothing shipped.

## 2026-08-04 · `.gitignore` patterns anchored to the repository root
Context   : `build/` without a leading slash matches at any depth, so
            `src/knowledge_base/build/` was never tracked — numbering_sim,
            frames, emitter, compile and publish, including two of the four
            artefacts the plan lists as verified. `make check` passed in the
            working tree and failed in a clean clone with
            `ModuleNotFoundError: No module named 'knowledge_base.build'`.
Chosen    : Every ignore path anchored with a leading slash; the five modules
            committed. isort's first-party list declared in `pyproject.toml`
            rather than inferred, since the inference depended on the same
            missing directory and gave different answers in the two checkouts.
Authority : plan §I-1 (the repo tracks code) · fallback ordering rule 4 — an
            untracked module is silent loss
Reversal  : cheap, but do not: this is the defect that makes a checkout differ
            from the repository.

## 2026-08-04 · Phase 3's field mismatch reported, not decided
Context   : CLAUDE.md and plan Phase 3 both require this to be raised once,
            before Phase 3, and not stopped on earlier. The configured fields
            hold no board captures; the ~200 board photographs are Linear
            Algebra and Abstract Algebra.
Chosen    : Built all Phase 3 *code* — photo chain, continuation, figures,
            audit — and reported the choice in `docs/SETUP-REPORT.md` rather
            than promoting either subject to a field. Building a book for a
            subject the owner did not ask for is the expensive error; the
            reversible one is to ask at the point where it matters.
Authority : plan Phase 3 prerequisite · CLAUDE.md "One thing to raise with the
            owner, once, before Phase 3"
Reversal  : n/a — nothing was decided.

## 2026-08-14 · `.gitattributes` added to enforce LF, `prompt_hash` is byte-sensitive
Context   : `extract/prompts.py:34` computes `prompt_hash` — recorded in every
            item's provenance — from `template.read_bytes()`, the raw bytes of
            `prompts/*.j2`. Nothing in the repository fixed line endings, so a
            CRLF checkout produces a different `prompt_hash` than an LF
            checkout for byte-for-byte the same template, silently. Found by a
            Windows session (CRLF checkout, differing hash); confirmed on
            Linux (this checkout is LF-only, `git add --renormalize .`
            changed nothing).
Chosen    : Added `.gitattributes` at the repo root: `* text=auto eol=lf` plus
            explicit `eol=lf` for every tracked text extension
            (`.py .j2 .yaml .yml .md .txt .typ .toml .sh .patch .lock`,
            `.gitignore`, `Makefile`, `bin/pre-commit`), and `binary` for
            `.pdf/.otf/.ttf`. Added `tests/test_prompts.py::test_templates_are_lf_only`,
            asserting no `\r` byte in `prompts/extract.md.j2` or
            `prompts/audit.md.j2` — this fails loudly on a CRLF checkout
            instead of silently changing provenance.
Authority : CLAUDE.md hard rules (provenance) · plan §I-3 (provenance is
            permanent) — a hash that depends on checkout config rather than
            content is not reproducible provenance.
Reversal  : cheap to add attributes; the test is a guard, not a behavior
            change — do not remove either without also fixing `prompts.py`
            to normalize line endings before hashing.
