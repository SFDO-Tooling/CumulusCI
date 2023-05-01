.PHONY: clean clean-test clean-pyc clean-build docs help
.DEFAULT_GOAL := help
define BROWSER_PYSCRIPT
import sys
from cumulusci.utils.fileutils import view_file
view_file(sys.argv[1])
endef
export BROWSER_PYSCRIPT

define PRINT_HELP_PYSCRIPT
import re, sys

for line in sys.stdin:
	match = re.match(r'^([a-zA-Z_-]+):.*?## (.*)$$', line)
	if match:
		target, help = match.groups()
		print("%-20s %s" % (target, help))
endef
export PRINT_HELP_PYSCRIPT
BROWSER := python -c "$$BROWSER_PYSCRIPT"

help:
	@python -c "$$PRINT_HELP_PYSCRIPT" < $(MAKEFILE_LIST)

clean: clean-build clean-pyc clean-test ## remove all build, test, coverage and Python artifacts


clean-build: ## remove build artifacts
	rm -fr build/
	rm -fr pybuild/
	rm -fr dist/
	rm -fr .eggs/
	find . -name '*.egg-info' -exec rm -fr {} +
	find . -name '*.egg' -exec rm -f {} +

clean-pyc: ## remove Python file artifacts
	find . -name '*.pyc' -exec rm -f {} +
	find . -name '*.pyo' -exec rm -f {} +
	find . -name '*~' -exec rm -f {} +
	find . -name '__pycache__' -exec rm -fr {} +

clean-test: ## remove test and coverage artifacts
	rm -fr .tox/
	rm -f .coverage
	rm -fr htmlcov/
	rm -f output.xml
	rm -f report.html

lint: ## check style with flake8
	flake8 cumulusci tests

test: ## run tests quickly with the default Python
	pytest

test-all: ## run tests on every Python version with tox
	tox

# Use CLASS_PATH to run coverage for a subset of tests.
# $ make coverage CLASS_PATH="cumulusci/core/tests"
coverage: ## check code coverage quickly with the default Python
	coverage run --source cumulusci -m pytest $(CLASS_PATH)
	coverage report -m
	coverage html
	$(BROWSER) htmlcov/index.html

vcr: # remake VCR cassettes and run other integration tests
	cci org scratch qa pytest
	cci org scratch_delete pytest
	find . -name \Test*.yaml | xargs rm
	pytest --org qa --run-slow-tests -rs --replace-vcrs

slow_tests: vcr # remake VCR cassettes and run other integration tests
	cci org scratch_delete pytest
	pytest integration_tests/ --org pytest -rs

docs: ## generate Sphinx HTML documentation
	$(MAKE) -C docs clean
	$(MAKE) -C docs html
	$(BROWSER) docs/_build/html/index.html

servedocs: docs ## compile the docs watching for changes
	watchmedo shell-command -p '*.rst' -c '$(MAKE) -C docs html' -R -D .

release: clean ## package and upload a release
	python utility/pin_dependencies.py
	hatch build
	hatch publish

dist: clean ## builds source and wheel package
	hatch build
	ls -l dist

install: clean ## install the package to the active Python's site-packages
	python -m pip install .

tag: clean
	git tag -a -m 'version $$(hatch version)' v$$(hatch version)
	git push --follow-tags

update-deps:
	echo Use the _Update Python Dependencies_ Github action for real releases
	pip-compile --upgrade --resolver=backtracking --output-file=requirements/prod.txt pyproject.toml
	pip-compile --upgrade --resolver=backtracking --output-file=requirements/dev.txt --all-extras pyproject.toml

dev-install:
	python -m pip install --upgrade pip pip-tools setuptools
	pip-sync requirements/*.txt
	python -m pip install -e .

schema:
	python -c 'from cumulusci.utils.yaml import cumulusci_yml; open("cumulusci/schema/cumulusci.jsonschema.json", "w").write(cumulusci_yml.CumulusCIRoot.schema_json(indent=4))'
	@pre-commit run prettier --files cumulusci/schema/cumulusci.jsonschema.json > /dev/null || true
	@echo cumulusci/schema/cumulusci.jsonschema.json
