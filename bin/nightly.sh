#!/usr/bin/env bash
# The nightly entry point (§I-12). Scheduled by Windows Task Scheduler via
#   wsl.exe -d Ubuntu -- /home/<user>/kb/bin/nightly.sh
# Keep this script trivial: everything that can fail belongs in Python, where it
# is tested and where a failure lands in the run report rather than in a shell
# exit code nobody sees.
set -uo pipefail
cd "$(dirname "$0")/.." || exit 1

if command -v uv >/dev/null 2>&1; then
  exec uv run --extra dev python -m knowledge_base.ops.nightly
fi
exec python3 -m knowledge_base.ops.nightly
