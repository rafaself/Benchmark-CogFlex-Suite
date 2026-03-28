PYTHON ?= .venv/bin/python
CLI := PYTHONPATH=src $(PYTHON) -m core.cli

.PHONY: help test doctor contract-audit compliance-check notebook-check validity reaudit integrity evidence-pass update-hashes

help:
	@printf "Public-safe (no private dataset required):\n"
	@printf "  make test            -- run the test suite\n"
	@printf "  make contract-audit  -- P0 public artifact contract audit\n"
	@printf "  make doctor          -- report environment status\n"
	@printf "\n"
	@printf "Private-required (need private_episodes.json mounted):\n"
	@printf "  make validity        -- R13 anti-shortcut gate\n"
	@printf "  make reaudit         -- R15 deterministic re-audit\n"
	@printf "  make integrity       -- frozen split integrity\n"
	@printf "  make evidence-pass   -- composite: test + validity + reaudit + integrity\n"
	@printf "\n"
	@printf "Other:\n"
	@printf "  make compliance-check  -- public/private isolation + notebook\n"
	@printf "  make notebook-check    -- notebook end-to-end smoke test\n"
	@printf "  make update-hashes     -- update canonical manifest hashes\n"

test:
	$(CLI) test

doctor:
	$(CLI) doctor

validity:
	$(CLI) validity

reaudit:
	$(CLI) reaudit

integrity:
	$(CLI) integrity

evidence-pass:
	$(CLI) evidence-pass

notebook-check:
	$(PYTHON) -m pytest tests/test_kbench_notebook.py -v

contract-audit:
	$(CLI) contract-audit

compliance-check:
	$(PYTHON) scripts/check_public_private_isolation.py
	$(PYTHON) -m pytest tests/test_kbench_notebook.py::TestNotebookEndToEnd -v

update-hashes:
	$(PYTHON) scripts/update_manifest_hashes.py
