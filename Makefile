.PHONY: help clean tools dist test_pypi pypi

.DEFAULT_GOAL := help

help: 	## Display this help message.
	@echo "Please use \`make <target>' where <target> is one of:"
	@awk -F ':.*?## ' '/^[a-zA-Z]/ && NF==2 {printf "  %-20s %s\n", $$1, $$2}' $(MAKEFILE_LIST) | sort

clean: 	## Remove stuff we don't need.
	find . -name '__pycache__' -exec rm -rf {} +
	rm -fr build/ dist/ src/*.egg-info
	rm -f get_*.json

tools:	## Install the development tools.
	python -m pip install -r dev-requirements.txt

dist: 	## Build the distributions.
	python -m build --sdist --wheel
	python -m twine check dist/*

test_pypi: ## Upload the distributions to PyPI's testing server.
	python -m twine upload --verbose --repository testpypi dist/*

pypi:	## Upload the built distributions to PyPI.
	python -m twine upload --verbose dist/*

pipx:	## Install locally as a command
	pipx install --force -e .
