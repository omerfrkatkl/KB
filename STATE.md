# State

The single live record of where this project stands. Every other status statement
in this repository is a dated historical report.

Updated only when the owner confirms a step is tested and approved.

---

## Position

**Last updated:** 2026-08-17

The repository is under version control and pushed to https://github.com/omerfrkatkl/KB
(first commit b6c3b7a, 148 files, the existing project state at plan revision 16).

The autonomous-operation protocol has been removed from the documentation (plan
revision 17). Work proceeds one step at a time under owner approval.

**The Windows port is complete.** Commits `3302651`..`aed125c` moved this
repository from the specified WSL2 Ubuntu host to native Windows, keeping the
code dual-platform. The suite reports **272 passed, 0 skipped, 0 failed**, and
every `make` target works. Recorded as plan revision 18 and in
`DECISIONS-TAKEN.md` (two entries, 2026-08-17).

## Open step

None. The port is finished and tested; the project is awaiting the owner's next
decision.

## Environment — settled

Native Windows, not WSL2. The code is dual-platform; this machine is Windows and
that is where every current claim was verified.

- `uv` 0.12.5 (scoop) — everything runs through `uv run --extra dev …`. A bare
  `python` on PATH resolves to the Microsoft Store stub, not an interpreter.
- Python 3.12.14, managed by `uv`; the project's `.venv` uses it.
- `typst` 0.15.1 (scoop), on PATH, **not vendored** — its version is verified
  against `template/TOOL-SHAS.txt` and a mismatch is a hard error. The fonts are
  still vendored and still verified by sha256.
- GNU `make` 4.4.1 (scoop), `git` 2.55.0.
- `rclone` is **not installed**. Anything that touches Google Drive cannot run.

## Decisions the owner still owes

- **Field mismatch.** The configured fields are Complex Analysis and Ordinary
  Differential Equations. The material in Drive is a Complex Analysis textbook PDF
  plus roughly 200 board photographs of Linear Algebra and Abstract Algebra, which
  are not configured fields. Phase 3 is board-driven and, as configured, has
  nothing to ingest. Either promote those two subjects to fields — each needs a
  field rule document, a profile, and two lines of config — or wait for board
  captures in a configured field.

## Known open items, none blocking

- **Queue filename collision.** Two entry ids that differ only where one has a
  colon and the other a hyphen sanitise to the same filename, and `add()` then
  returns the first entry's path without writing the second. Real silent loss of
  a queued decision, on a narrow trigger.
- **Console encoding.** The Windows console falls back to cp1254 here, which
  mangles non-ASCII output. Cosmetic in `knowledge-base status`, but
  `knowledge-base review` will display mathematics.
- **Unclosed file handle** in `tests/fixtures/synthetic/emit_v1.py`. Pre-existing
  and test-only; it affects nothing that ships.

## What is blocked, and on what

`docs/SETUP-REPORT.md` (2026-08-04) lists every remaining work package and what it
waits on. Nothing on that list waits on code; all of it waits on Google Drive
access and real captures.

## Standing caution

No extraction has ever been performed by this system. Every extraction-side claim
in this repository is unverified. `tests/fixtures/synthetic/` is a renderer
regression fixture and is never evidence about extraction quality —
`docs/SLICE-FINDINGS.md` records what it cost the one time generated material was
read as evidence.
