.PHONY: help clean tools dist test_pypi pypi pipx

.DEFAULT_GOAL := help

help: 	## Display this help message.
	@echo "Please use \`make <target>' where <target> is one of:"
	@awk -F ':.*?## ' '/^[a-zA-Z]/ && NF==2 {printf "  %-20s %s\n", $$1, $$2}' $(MAKEFILE_LIST) | sort

clean: 	## Remove stuff we don't need.
	find . -name '__pycache__' -exec rm -rf {} +
	rm -fr build/ dist/ src/*.egg-info
	rm -fr .coverage htmlcov/
	rm -fr .pytest_cache/
	rm -f get_*.json get_index.txt

tools:	## Install the development tools.
	python -m pip install -U --upgrade-strategy=eager -r dev-requirements.txt

test:	## Run the tests
	TZ=GMT coverage run -m pytest

dist: 	## Build the distributions.
	python -m build --sdist --wheel
	python -m twine check dist/*

test_pypi: ## Upload the distributions to PyPI's testing server.
	python -m twine upload --verbose --repository testpypi --password $$TWINE_TEST_PASSWORD dist/*

pypi:	## Upload the built distributions to PyPI.
	python -m twine upload --verbose dist/*

pipx:	## Install locally as a command
	pipx install --force -e .

.PHONY: cog_docs

cog_docs: _pip_install_e	## Run cog to get docs right
	python -m cogapp -crP --verbosity=1 README.rst

.PHONY: test_release release check_release

test_release: clean check_release dist test_pypi	## Do all the steps for a test release

release: _check_credentials clean check_release dist pypi tag gh_release comment	## Do all the steps for a release

_check_credentials:
	@if [[ -z "$$TWINE_PASSWORD" ]]; then \
		echo 'Missing TWINE_PASSWORD: opvars'; \
		exit 1; \
	fi
	@if [[ -z "$$GITHUB_TOKEN" ]]; then \
		echo 'Missing GITHUB_TOKEN: opvars github'; \
		exit 1; \
	fi

check_release: _check_manifest _check_tree _check_readme _check_version	## Check that we are ready for a release
	@echo "Release checks passed"

_pip_install_e:
	python -m pip install -q -e .

_check_manifest:
	python -m check_manifest

_check_tree:
	@if [[ -n $$(git status --porcelain) ]]; then \
		echo 'There are modified files! Did you forget to check them in?'; \
		exit 1; \
	fi

_check_readme: _pip_install_e
	@if grep -q Unreleased README.rst; then \
		echo 'I see Unreleased in README.rst! Did you forget to edit it?'; \
		exit 1; \
	fi
	@export VER="$$(python -c "import watchgha as me; print(me.__version__)")" && \
	if grep -q $$VER README.rst; then \
		echo 'Current version is in the README.rst'; \
	else \
		echo "No entry in README.rst for version $$VER!"; \
		exit 1; \
	fi
	python -m cogapp -cP --check --verbosity=1 README.rst

_check_version: _pip_install_e
	@export VER="$$(python -c "import watchgha as me; print(me.__version__)")" && \
	if [[ $$(git tags | grep -q -w $$VER && echo "x") == "x" ]]; then \
		echo 'A git tag for this version exists! Did you forget to bump the version in src/watchgha/__init__.py?'; \
		exit 1; \
	fi

.PHONY: tag gh_release comment

tag: _pip_install_e ## Make a git tag with the version number
	@export VER="$$(python -c "import watchgha as me; print(me.__version__)")" && \
	git tag -s -m "Version $$VER" $$VER
	git push --all

gh_release:	## Publish a GitHub release
	python -m scriv github-release --all

comment:	## Show the markdown for a "shipped" comment.
	@export VER="$$(python -c "import watchgha as me; print(me.__version__)")" && \
	echo "Use this comment on issues and pull requests:" && \
	echo "   This is now released as part of [watchgha $$VER](https://pypi.org/project/watchgha/$$VER)."
