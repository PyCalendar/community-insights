.DEFAULT_GOAL = help
SHELL         = bash
PYTHONVERSION = >=3.13,<3.15
PORT         ?= 5000
WINDOW       ?= 1280x900
BASE         ?= origin/main
ZIZMOR        = zizmor==1.30.1
VALE          = uvx --quiet --with docutils==0.22.4 vale==3.24.0.0

.PHONY: help
help:  # This help message
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-30s\033[0m %s\n", $$1, $$2}'

.venv:  ## Install required Python, create Python virtual environment, and install requirements
	@uv python install "$(PYTHONVERSION)"
	@uv venv --python "$(PYTHONVERSION)"
	@uv sync --group dev
	@uv run pre-commit install || true  # not in a git checkout

.PHONY: init
init: clean-python .venv browsers run-prepare  ## Recreate the environment, the browser of the tests and the test site: then make run

# The Firefox of Playwright for the browser tests. PLAYWRIGHT_FLAGS=--with-deps also installs
# the libraries of the system it needs (the CI; needs sudo).
PLAYWRIGHT_FLAGS ?=
.PHONY: browsers
browsers: .venv  ## Install the Firefox of Playwright for the browser tests
	@uv run playwright install $(PLAYWRIGHT_FLAGS) firefox

# The JavaScript and CSS the pages load, from the npm packages in package.json: the exact
# versions are in package-lock.json, so make vendor gives the same files every time. The
# source maps are left out (their links too): the files would be too big for the repository.
VENDOR = static/vendor
.PHONY: vendor
vendor:  ## Copy the JavaScript and CSS of the pages from node_modules into static/vendor
	@npm ci --no-audit --no-fund
	@mkdir -p $(VENDOR)/bootstrap $(VENDOR)/chartjs $(VENDOR)/sortable $(VENDOR)/htmx
	@cp node_modules/bootstrap/dist/css/bootstrap.min.css $(VENDOR)/bootstrap/
	@cp node_modules/bootstrap/dist/js/bootstrap.bundle.min.js $(VENDOR)/bootstrap/
	@cp node_modules/bootstrap/LICENSE $(VENDOR)/bootstrap/LICENSE.txt
	@cp node_modules/chart.js/dist/chart.umd.js $(VENDOR)/chartjs/
	@cp node_modules/chartjs-chart-matrix/dist/chartjs-chart-matrix.min.js $(VENDOR)/chartjs/
	@cp node_modules/chart.js/LICENSE.md $(VENDOR)/chartjs/LICENSE.md
	@cp node_modules/sortablejs/Sortable.min.js $(VENDOR)/sortable/
	@cp node_modules/sortablejs/LICENSE $(VENDOR)/sortable/LICENSE.txt
	@cp node_modules/htmx.org/dist/htmx.min.js $(VENDOR)/htmx/
	@cp node_modules/htmx.org/LICENSE $(VENDOR)/htmx/LICENSE.txt
	@sed -i -e '/^\/\*# sourceMappingURL=.*\*\/$$/d' -e '/^\/\/# sourceMappingURL=/d' $(VENDOR)/*/*.js $(VENDOR)/*/*.css
	@echo "static/vendor is updated; list new versions in static/vendor/vendor.json and REUSE.toml"

.PHONY: clean-python
clean-python:
	rm -rf .venv/

.PHONY: migrate
migrate: .venv  ## Create or update the database
	@uv run python manage.py migrate

.PHONY: run-prepare
run-prepare: migrate  ## Prepare the database of the test site: superuser admin@example.com (password admin) and a demo project
	@uv run python manage.py invalidate_cachalot -v0
	@uv run python manage.py ensure_superuser admin@example.com:admin
	@uv run python manage.py demo_data admin@example.com

.PHONY: run
run: run-prepare  ## Run the server on $(PORT), fetches in a thread of it (FETCH_WORKER=internal); data in ./data like make docker-run
	@PRODUCTION=false DEBUG=1 FETCH_WORKER=internal uv run python manage.py runserver "$(PORT)"

.PHONY: test
test: .venv  ## Run the Python tests, with coverage, and check that no migration is missing
	@uv run python manage.py makemigrations --check --dry-run
	@uv run pytest --cov=community_insights --cov-branch --cov-report=xml --cov-report=term

.PHONY: test-performance
test-performance: .venv  ## Measure the speed: statistics on large made up data, and reading GitHub with $$GITHUB_TOKEN
	@uv run pytest -m performance -s -p no:cacheprovider

.PHONY: check-vendor
check-vendor:  ## Check that static/vendor is what make vendor copies from package-lock.json
	@rm -rf .cache/vendor
	@$(MAKE) --no-print-directory vendor VENDOR=.cache/vendor
	@diff -r --exclude=vendor.json .cache/vendor static/vendor

.PHONY: check-site-links
check-site-links: .venv  ## Check every link of the running site, signed in, with linkchecker
	@./tests/linkchecker/check-site.sh

GITHUB_SCHEMA ?= .cache/github-schema.graphql

.PHONY: check-graphql
check-graphql: .venv  ## Validate every GraphQL query of the site against the schema GitHub publishes
	@mkdir -p $(dir $(GITHUB_SCHEMA))
	@curl -sSfL -o $(GITHUB_SCHEMA) https://docs.github.com/public/fpt/schema.docs.graphql
	@GITHUB_SCHEMA=$(GITHUB_SCHEMA) uv run pytest -q -p no:cacheprovider tests/github/test_github_schema.py

.PHONY: test-js
test-js: node_modules  ## Run the tests of the JavaScript with node (jsdom from package-lock.json)
	@npm test

node_modules: package.json package-lock.json
	@npm ci --no-audit --no-fund
	@touch node_modules

.PHONY: test-browser
test-browser: .venv  ## Run the browser tests with Firefox and Playwright (WINDOW=375x812 for a phone)
	@WINDOW="$(WINDOW)" uv run pytest -m browser tests/browser --browser firefox -p no:cacheprovider $(BROWSER_FLAGS)

.PHONY: test-all
test-all: lint typecheck test test-js test-browser check-graphql check-site-links check-vendor build docs vale linkcheck reuse zizmor  ## Run all tests and checks

.PHONY: worker
worker: migrate  ## Run the fetch worker alone, as with FETCH_WORKER=external-separate-container
	@uv run python manage.py fetch_worker

.PHONY: lint
lint: .venv  ## Check the code style
	@uv run ruff check .
	@uv run ruff format --check .

# How manage.py is run; "python manage.py" in a container without uv.
MANAGE ?= uv run python manage.py
LANGUAGES ?= de
MESSAGES_IGNORE = -i '.venv/*' -i 'docs/*' -i 'tests/*' -i 'features/*' \
	-i 'staticfiles/*' -i 'node_modules/*' -i 'static/vendor/*'

.PHONY: messages
messages:  ## Update the translations in locale/ and compile them; needs GNU gettext
	@for language in $(LANGUAGES); do \
		$(MANAGE) makemessages -l $$language $(MESSAGES_IGNORE) --no-location && \
		$(MANAGE) makemessages -d djangojs -l $$language $(MESSAGES_IGNORE) --no-location \
			|| exit 1; \
	done
	@$(MANAGE) compilemessages -i '.venv' -i 'node_modules'

.PHONY: test-translations
test-translations: messages  ## Update the translations and check that all texts are translated
	@uv run pytest tests/i18n -q

.PHONY: typecheck
typecheck: .venv  ## Check the type hints with pyright (django-types)
	@uv run pyright

.PHONY: docs
docs:  ## Build the documentation into docs/_build/html; warnings and broken references fail
	@uv run --extra docs sphinx-build -W -n --keep-going -b html docs docs/_build/html

.PHONY: build
build:  ## Build the package into dist/, as pip install .[docs] does on Read the Docs
	@uv build -o dist

.PHONY: livehtml
livehtml:  ## Show the documentation while editing it, rebuilt on every change
	@uv run --extra docs sphinx-autobuild docs docs/_build/html

.PHONY: linkcheck
linkcheck:  ## Check that the links of the documentation work (needs the internet)
	@uv run --extra docs sphinx-build -W --keep-going -b linkcheck docs docs/_build/linkcheck \
		|| uv run python -m tests.linkchecker.docs docs/_build/linkcheck/output.json

.PHONY: changelog
changelog:  ## Check that there is a news fragment compared to BASE (default origin/main)
	@uv run --extra docs towncrier check --compare-with "$(BASE)"

.PHONY: reuse
reuse:  ## Check the licensing (REUSE)
	@uvx --quiet reuse lint

.PHONY: vale
vale:  ## Check the prose of the documentation with Vale; errors fail, suggestions are shown
	@$(VALE) sync
	@$(VALE) docs/

.PHONY: zizmor
zizmor:  ## Check the security of the GitHub Actions workflows
	@uvx --quiet $(ZIZMOR) .github/workflows/

.PHONY: zizmor-sarif
zizmor-sarif:  ## zizmor as zizmor-results.sarif, for GitHub code scanning
	@uvx --quiet $(ZIZMOR) --format sarif .github/workflows/ > zizmor-results.sarif

.PHONY: clear-cache
clear-cache: migrate  ## Delete cached repositories not used for 30 days
	@uv run python manage.py clear_cache --days 30

.PHONY: version
version:  ## Write the build information (commit, date) into community_insights/version.json
	@./docker/set-version.sh

.PHONY: docker-build
docker-build: version  ## Build the container
	docker build -t community-insights .

.PHONY: docker-build-all
docker-build-all: version  ## Build the container for amd64 and arm64, like the published image (needs buildx)
	docker buildx build --platform linux/amd64,linux/arm64 -t community-insights .

.PHONY: docker-test
docker-test: docker-build  ## Run the container and check that it is healthy
	@docker rm -f community-insights-test >/dev/null 2>&1 || true
	@docker run -d --name community-insights-test -p 5099:5000 -e PRODUCTION=false \
		-e DEFAULT_SUPERUSER=admin@example.com:admin community-insights >/dev/null
	@for i in $$(seq 60); do curl -sf http://localhost:5099/health/ >/dev/null && echo healthy && break; sleep 1; done; \
	healthy=$$(curl -sf http://localhost:5099/health/ >/dev/null && echo yes); \
	[ "$$healthy" = yes ] || docker logs community-insights-test; \
	docker rm -f community-insights-test >/dev/null; [ "$$healthy" = yes ]

.PHONY: docker-run
docker-run: docker-build  ## Run the container on $(PORT) with the database of make run (./data) and the superuser admin@example.com
	@mkdir -p data
	docker run --rm -p "$(PORT):5000" -v "$(CURDIR)/data:/app/data" --user "$$(id -u):$$(id -g)" \
		-e DEFAULT_SUPERUSER=admin@example.com:admin -e PRODUCTION=false $(if $(wildcard .env),--env-file .env) community-insights
