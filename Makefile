# Capture extra CLI arguments as ARGS
ARGS ?= $(filter-out $@,$(MAKECMDGOALS))

# Prevent make from treating extra args as targets
%:
	@:

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


# -----------------------------
# Setup
# -----------------------------
setup:
	uv sync --all-groups

# -----------------------------
# Testing
# -----------------------------

test:
	uv run coverage run -a --concurrency=thread,greenlet -m pytest $(ARGS)

cov:
	uv run coverage report
	uv run coverage xml

# -----------------------------
# Linting
# -----------------------------

lint:
	uv run ruff check $(ARGS)
	uv run ruff format --check $(ARGS)
	uv run mypy $(ARGS)

format:
	uv run ruff format $(ARGS)
	uv run ruff check --fix $(ARGS)

secure:
	uv run bandit -r sqladmin --config pyproject.toml

# -----------------------------
# Documentation
# -----------------------------

docs-build:
	uv run mkdocs build

docs-serve:
	uv run mkdocs serve --dev-addr localhost:8080

docs-deploy:
	uv run mkdocs gh-deploy --force


# -----------------------------
# Publish
# -----------------------------

build:
	uv build


publish:
	uv publish


.PHONY: setup test cov lint-check lint-format docs-build docs-serve docs-deploy build publish
