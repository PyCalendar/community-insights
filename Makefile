.DEFAULT_GOAL = help
SHELL         = bash
PYTHONVERSION = >=3.13,<3.15

.PHONY: help
help:  # This help message
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-30s\033[0m %s\n", $$1, $$2}'

.venv:  ## Install required Python, create Python virtual environment, and install requirements
	@uv python install "$(PYTHONVERSION)"
	@uv venv --python "$(PYTHONVERSION)"
	@uv sync --group dev
	@uv run pre-commit install

.PHONY: init
init: clean-python .venv  ## Recreate the Python virtual environment and install requirements

.PHONY: clean-python
clean-python:
	rm -rf .venv/

.PHONY: test
test: .venv  ## Run the tests
	@uv run pytest

BINDIR ?= $(HOME)/.local/bin

.PHONY: install-dev
install-dev: .venv  ## Link gh-community from the local .venv into BINDIR (editable)
	@mkdir -p "$(BINDIR)"
	@ln -sf "$(realpath .venv/bin/gh-community)" "$(BINDIR)/gh-community"
	@echo "Linked $(BINDIR)/gh-community -> .venv/bin/gh-community"
	@$(MAKE) --no-print-directory install-completion

.PHONY: install
install:  ## Install gh-community with pipx (editable)
	@pipx install --force --editable .
	@$(MAKE) --no-print-directory install-completion

.PHONY: install-completion
install-completion: .venv  ## Install shell completion for gh-community
	@uv run gh-community --install-completion
	@echo "Open a new terminal (or source ~/.bashrc) to use the completion."
