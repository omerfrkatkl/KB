# State

The single live record of where this project stands. Every other status statement
in this repository is a dated historical report.

Updated only when the owner confirms a step is tested and approved.

---

## Position

**Last updated:** 2026-08-17

The repository is under version control and pushed to https://github.com/omerfrkatkl/KB
(first commit b6c3b7a, 148 files, the existing project state at plan revision 16).

Work has resumed after a pause. The autonomous-operation protocol has been removed
from the documentation (plan revision 17). Work now proceeds one step at a time
under owner approval.

## Open step

Documentation edit removing the autonomous-operation layer — awaiting owner review.

## Environment — unsettled, blocking

The specification assumes WSL2 Ubuntu, Python 3.12, `uv`. The working copy is on
native Windows with Python 3.14 and no `uv`. Nothing has been installed and the
test suite has never been run on this machine, so no claim about the current build
state has been verified here.

Until this is settled, no command that builds, installs or tests may be run.

## Decisions the owner still owes

- **Environment.** WSL2 as specified, or native Windows with the POSIX assumptions
  reworked.
- **Field mismatch.** The configured fields are Complex Analysis and Ordinary
  Differential Equations. The material in Drive is a Complex Analysis textbook PDF
  plus roughly 200 board photographs of Linear Algebra and Abstract Algebra, which
  are not configured fields. Phase 3 is board-driven and, as configured, has
  nothing to ingest. Either promote those two subjects to fields — each needs a
  field rule document, a profile, and two lines of config — or wait for board
  captures in a configured field.

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
