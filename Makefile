.PHONY: bootstrap check rules hooks clean

# Run inside the project environment when uv is available, so `make check` means
# the same thing on a fresh clone as it does anywhere else. Without uv, fall back
# to whatever python3/ruff/pytest are on PATH — the commands are identical.
#
# Detected the same way the `hooks` target resolves its shell below: GNU Make
# for Windows runs $(shell ...) through cmd.exe, where `command -v` does not
# exist and always returns empty, so a POSIX-only probe would wrongly report
# uv as absent even when it is on PATH. Branch on $(OS) and use a cmd-native
# probe on Windows, `command -v` on POSIX.
ifeq ($(OS),Windows_NT)
  UV := $(shell where uv)
else
  UV := $(shell command -v uv 2>/dev/null)
endif
ifdef UV
  RUN := uv run --extra dev
  PY  := uv run --extra dev python
else
  RUN :=
  PY  := python3
endif

bootstrap:            ## fetch pinned typst + fonts into tools/ and fonts/, verify sha256
	$(PY) -m knowledge_base.ops.bootstrap

check:                ## the gate for every work package
	$(RUN) ruff check src tests
	$(RUN) pytest -q

rules:                ## compile rules/ -> generated/ (lexicon, symbols, validators)
	$(PY) -m knowledge_base.rules.compile_rules
	@git diff --quiet generated/ || echo "generated/ changed — review and commit"

# Resolve a real POSIX shell to run install-hooks.sh with, rather than
# trusting the name `bash` on PATH: on Windows, `bash` found via PATH may be
# the zero-byte WSL launcher stub that ships with Windows itself — invoking
# it silently drops into a WSL2 Ubuntu instance and runs the script against
# Linux paths instead of this checkout. Prefer, in order: `sh` if it
# resolves to a real shell, then Git for Windows' bundled sh.exe, then
# `bash`. On a POSIX machine `sh` is real, so it is used directly.
ifeq ($(OS),Windows_NT)
  SH_ON_PATH := $(shell where sh)
  GIT_SH := C:/Program Files/Git/bin/sh.exe
  ifneq ($(strip $(SH_ON_PATH)),)
    HOOK_SHELL := sh
  else ifneq ($(shell if exist "$(GIT_SH)" echo yes),)
    HOOK_SHELL := $(GIT_SH)
  else
    HOOK_SHELL := bash
  endif
else
  HOOK_SHELL := $(shell command -v sh 2>/dev/null || command -v bash)
endif

hooks:                ## install the pre-commit guard from bin/
	"$(HOOK_SHELL)" bin/install-hooks.sh

clean:
	$(PY) -B -m knowledge_base.ops.clean
