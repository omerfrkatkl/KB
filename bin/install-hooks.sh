#!/usr/bin/env bash
# Point git at the tracked hooks in bin/ so the guard lives with the code
# rather than in an untracked .git/hooks copy that drifts. Using
# core.hooksPath achieves this without creating a symlink, which Windows
# does not grant permission to create by default.
set -euo pipefail
root="$(git rev-parse --show-toplevel)"

if [ -e "$root/.git/hooks/pre-commit" ]; then
  echo "note: $root/.git/hooks/pre-commit already exists; core.hooksPath takes precedence over it, so that file is now inert. It has been left in place, not deleted."
fi

git -C "$root" config core.hooksPath bin
echo "configured core.hooksPath = bin (git will now run bin/pre-commit as the pre-commit hook)"
