actions = \
	test \
	cov \
	lint-check \
	lint-format \
	docs-build \
	docs-serve \
	docs-deploy \
	build \
	publish


# Use uv to run all commands
UV = uv run

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
	$(UV) ruff .
	$(UV) ruff format --check .
	$(UV) mypy sqladmin

format:
	$(UV) ruff format .
	$(UV) ruff --fix .

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
	$(UV) build


publish:
	$(UV) publish


.PHONY: test cov lint-check lint-format docs-build docs-serve docs-deploy build publish
