# Capture extra CLI arguments as ARGS
ARGS ?= $(filter-out $@,$(MAKECMDGOALS))

# Prevent make from treating extra args as targets
%:
	@:

PY_ARGS := $(filter %.py,$(ARGS))

actions = \
	setup \
	test \
	cov \
	lint-check \
	lint-format \
	docs-build \
	docs-serve \
	docs-deploy \
	build \
	publish

# ARGS used for `test`. `PY_ARGS` used for `lint` and `format`
PY_ARGS := $(or $(filter %.py,$(ARGS)),sqladmin)


# Use uv to run all commands
UV = uv run

setup:
	uv sync --all-groups

# -----------------------------
# Testing
# -----------------------------

test:
	$(UV) coverage run -a --concurrency=thread,greenlet -m pytest $(ARGS)

cov:
	$(UV) coverage report --show-missing --skip-covered --fail-under=99
	$(UV) coverage xml

# -----------------------------
# Linting
# -----------------------------

lint:
	$(UV) ruff check $(PY_ARGS)
	$(UV) ruff format --check $(PY_ARGS)
	$(UV) mypy $(PY_ARGS)
	$(UV) pylint $(PY_ARGS)

format:
	$(UV) ruff format $(PY_ARGS)
	$(UV) ruff --fix $(PY_ARGS)

# -----------------------------
# Documentation
# -----------------------------

docs-build:
	$(UV) mkdocs build

docs-serve:
	$(UV) mkdocs serve --dev-addr localhost:8080

docs-deploy:
	$(UV) mkdocs gh-deploy --force


# -----------------------------
# Publish
# -----------------------------

build:
	uv build


publish:
	uv publish


.PHONY: setup test cov lint-check lint-format docs-build docs-serve docs-deploy build publish
