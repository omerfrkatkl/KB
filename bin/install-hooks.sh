#!/usr/bin/env bash
# Point git at the tracked hooks in bin/ so the guard lives with the code
# rather than in an untracked .git/hooks copy that drifts.
set -euo pipefail
root="$(git rev-parse --show-toplevel)"
ln -sf ../../bin/pre-commit "$root/.git/hooks/pre-commit"
chmod +x "$root/bin/pre-commit"
echo "pre-commit hook installed -> bin/pre-commit"
