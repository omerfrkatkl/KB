.PHONY: bootstrap check rules hooks clean

# Run inside the project environment when uv is available, so `make check` means
# the same thing on a fresh clone as it does anywhere else. Without uv, fall back
# to whatever python3/ruff/pytest are on PATH — the commands are identical.
UV := $(shell command -v uv 2>/dev/null)
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

hooks:                ## install the pre-commit guard from bin/
	bash bin/install-hooks.sh

clean:
	rm -rf build/ .pytest_cache **/__pycache__
