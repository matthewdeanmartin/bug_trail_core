# isort . && black . && bandit -r . && pylint && pre-commit run --all-files
# Get changed files

FILES := $(wildcard **/*.py)

# if you wrap everything in uv run, it runs slower.
ifeq ($(origin VIRTUAL_ENV),undefined)
    VENV := uv run
else
    VENV :=
endif

uv.lock: pyproject.toml
	@echo "Installing dependencies"
	@uv sync

clean-pyc:
	@echo "Removing compiled files"
# 	@find bug_trail_core -name '*.pyc' -exec rm -f {} + || true
#	@find bug_trail_core -name '*.pyo' -exec rm -f {} + || true
#	@find bug_trail_core -name '__pycache__' -exec rm -fr {} + || true

clean-test:
	@echo "Removing coverage data"
	@rm -f .coverage || true
	@rm -f .coverage.* || true

clean: clean-pyc clean-test

# tests can't be expected to pass if dependencies aren't installed.
# tests are often slow and linting is fast, so run tests on linted code.
test: clean uv.lock
	@echo "Running unit tests"
	$(VENV) pytest --doctest-modules bug_trail_core
	# $(VENV) python -m unittest discover
	$(VENV) py.test tests -vv -n 2 --cov=bug_trail_core --cov-report=html --cov-fail-under 70
	$(VENV) bash basic_test.sh


.build_history:
	@mkdir -p .build_history

.build_history/isort: .build_history $(FILES)
	@echo "Formatting imports"
	$(VENV) isort .
	@touch .build_history/isort

.PHONY: isort
isort: .build_history/isort

.build_history/black: .build_history .build_history/isort $(FILES)
	@echo "Formatting code"
	$(VENV) black bug_trail_core --exclude .venv
	$(VENV) black tests --exclude .venv
	# $(VENV) black scripts --exclude .venv
	@touch .build_history/black
	[ -n "$$CI" ] && echo "Skipping coderoller-flatten-repo in CI" || $(VENV) coderoller-flatten-repo bug_trail_core


.PHONY: black
black: .build_history/black

.build_history/pre-commit: .build_history .build_history/isort .build_history/black
	@echo "Pre-commit checks"
	$(VENV) pre-commit run --all-files
	@touch .build_history/pre-commit

.PHONY: pre-commit
pre-commit: .build_history/pre-commit

.build_history/bandit: .build_history $(FILES)
	@echo "Security checks"
	$(VENV)  bandit bug_trail_core -r
	@touch .build_history/bandit

.PHONY: bandit
bandit: .build_history/bandit

.PHONY: pylint
.build_history/pylint: .build_history .build_history/isort .build_history/black $(FILES)
	@echo "Linting with pylint"
	$(VENV) ruff --fix
	$(VENV) pylint bug_trail_core --fail-under 9.8
	@touch .build_history/pylint

# for when using -j (jobs, run in parallel)
.NOTPARALLEL: .build_history/isort .build_history/black

check: mypy test pylint bandit pre-commit

.PHONY: publish
publish: test
	rm -rf dist && hatchling build

.PHONY: mypy
mypy:
	$(VENV) mypy bug_trail_core --ignore-missing-imports --check-untyped-defs


check_docs:
	$(VENV) interrogate bug_trail_core --verbose
	$(VENV) pydoctest --config .pydoctest.json | grep -v "__init__" | grep -v "__main__" | grep -v "Unable to parse"

make_docs:
	pdoc bug_trail_core --html -o docs --force

check_md:
	$(VENV) mdformat README.md docs/*.md
	$(VENV) linkcheckMarkdown README.md
	$(VENV) markdownlint README.md --config .markdownlintrc

check_spelling:
	$(VENV) pylint bug_trail_core --enable C0402 --rcfile=.pylintrc_spell
	$(VENV) codespell README.md --ignore-words=private_dictionary.txt
	$(VENV) codespell bug_trail_core --ignore-words=private_dictionary.txt

check_changelog:
	# pipx install keepachangelog-manager
	$(VENV) changelogmanager validate

check_all_docs: check_docs check_md check_spelling check_changelog

check_own_ver:
	# Can it verify itself?
	$(VENV) ./dog_food.sh

#audit:
#	# $(VENV) python -m bug_trail_core audit
#	$(VENV) tool_audit single bug_trail_core --version=">=2.0.0"