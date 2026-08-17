"""runner.py — the one place a language model is invoked (§I-7).

    cat <staged>/prompt.md | claude -p --output-format json --bare --allowedTools "Read"

Images are staged on disk and the prompt lists their absolute paths. Claude Code
is shelled out to; it is never a Python dependency.

**Record/replay is not a testing convenience, it is the architecture.** Every
call's inputs digest and full envelope are written to `state/calls/`, and
`KB_REPLAY=1` makes this module serve the recorded envelope instead of spending a
call. That is what makes every stage after extraction testable offline, and it is
what lets a parked batch be re-run through changed validation without paying for
the extraction again.

Failure policy, from §I-7:
  schema-invalid inner JSON -> up to 2 retries with the validator errors appended
  then park the batch
  rate-limit signature       -> requeue and halt extraction for the run
  timeout (25 min)           -> kill and requeue
"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from knowledge_base.config import ROOT
from knowledge_base.extract.contract import (
    ContractError,
    Extraction,
    RateLimited,
    envelope_text,
    parse_audit,
    parse_extraction,
)
from knowledge_base.ops.log import get

log = get("runner")

TIMEOUT_SECONDS = 25 * 60
MAX_RETRIES = 2


@dataclass
class CallRecord:
    call_id: str
    batch_id: str
    kind: str                 # extract | audit
    prompt_sha256: str
    prompt_hash: str          # the pack's own hash, recorded into provenance
    started: str
    finished: str
    returncode: int
    envelope: str
    attempt: int
    images: list[str] = field(default_factory=list)
    model: str | None = None


class Parked(RuntimeError):
    """The batch could not be parsed after its retries. It stays on disk with
    the responses attached, so a prompt fix can re-run it without a new call."""


def call_id(batch_id: str, prompt: str, attempt: int) -> str:
    digest = hashlib.sha256(prompt.encode("utf-8")).hexdigest()[:16]
    return f"{batch_id}-{attempt}-{digest}"


def calls_dir(root: Path = ROOT) -> Path:
    return Path(root) / "state" / "calls"


def replaying() -> bool:
    return os.environ.get("KB_REPLAY") == "1"


def record(rec: CallRecord, root: Path = ROOT) -> Path:
    d = calls_dir(root)
    d.mkdir(parents=True, exist_ok=True)
    path = d / f"{rec.call_id}.json"
    payload = rec.__dict__
    tmp = path.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8", newline="")
    tmp.replace(path)
    return path


def recorded(cid: str, root: Path = ROOT) -> CallRecord | None:
    path = calls_dir(root) / f"{cid}.json"
    if not path.exists():
        return None
    return CallRecord(**json.loads(path.read_text(encoding="utf-8")))


def invoke(prompt: str, *, batch_id: str, kind: str, prompt_hash: str,
           attempt: int = 0, model: str | None = None,
           root: Path = ROOT, timeout: int = TIMEOUT_SECONDS) -> CallRecord:
    """One call. Serves a recording under KB_REPLAY=1, otherwise shells out."""
    cid = call_id(batch_id, prompt, attempt)
    if replaying():
        rec = recorded(cid, root)
        if rec is None:
            raise Parked(
                f"KB_REPLAY=1 but no recording for {cid}. Replay never calls the "
                "model — record the call first, or point KB_REPLAY at the right root.")
        log.info("replay %s", cid)
        return rec

    cmd = ["claude", "-p", "--output-format", "json", "--bare",
           "--allowedTools", "Read"]
    if model and model != "default":
        cmd += ["--model", model]

    started = _now()
    try:
        proc = subprocess.run(cmd, input=prompt, capture_output=True, text=True,
                              timeout=timeout)
        returncode, out, err = proc.returncode, proc.stdout, proc.stderr
    except subprocess.TimeoutExpired:
        log.warning("batch %s timed out after %ds — requeueing", batch_id, timeout)
        returncode, out, err = -9, "", f"timeout after {timeout}s"
    except FileNotFoundError as e:
        raise Parked(
            "the `claude` CLI is not on PATH. The pipeline shells out to it and "
            "never imports it; install and log in inside the runtime host.") from e

    rec = CallRecord(call_id=cid, batch_id=batch_id, kind=kind,
                     prompt_sha256=hashlib.sha256(prompt.encode()).hexdigest(),
                     prompt_hash=prompt_hash, started=started, finished=_now(),
                     returncode=returncode, envelope=out or err, attempt=attempt,
                     model=model)
    record(rec, root)
    return rec


def run_extraction(build_prompt, *, batch_id: str, prompt_hash: str,
                   model: str | None = None, root: Path = ROOT) -> Extraction:
    """Call, parse, and retry with the validator's own errors appended.

    `build_prompt(errors)` returns the prompt text; on a retry it is handed the
    previous failure so the pack can append it. Telling the model exactly what
    was wrong is what makes two retries enough.
    """
    errors: str | None = None
    for attempt in range(MAX_RETRIES + 1):
        prompt = build_prompt(errors)
        rec = invoke(prompt, batch_id=batch_id, kind="extract",
                     prompt_hash=prompt_hash, attempt=attempt, model=model, root=root)
        if rec.returncode != 0 and not rec.envelope.strip():
            raise Parked(f"batch {batch_id}: the call failed with no output "
                         f"(returncode {rec.returncode})")
        try:
            return parse_extraction(envelope_text(rec.envelope))
        except RateLimited:
            # §I-7: requeue and stop extraction for this run.
            log.warning("rate limit on batch %s — halting extraction", batch_id)
            raise
        except ContractError as e:
            errors = str(e)
            log.warning("batch %s attempt %d did not match the contract: %s",
                        batch_id, attempt, errors.splitlines()[0][:200])
    raise Parked(f"batch {batch_id}: the response did not match the contract after "
                 f"{MAX_RETRIES} retries. The envelopes are in state/calls/; fix the "
                 f"prompt and re-run — no new call is needed to test the fix.\n{errors}")


def run_audit(prompt: str, *, batch_id: str, prompt_hash: str,
              model: str | None = None, root: Path = ROOT):
    rec = invoke(prompt, batch_id=f"{batch_id}-audit", kind="audit",
                 prompt_hash=prompt_hash, model=model, root=root)
    return parse_audit(envelope_text(rec.envelope))


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")
