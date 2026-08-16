.DELETE_ON_ERROR:

all:
	echo >&2 "Must specify target."

test:
	python -m pytest --cov=osxcollector --cov-report=term-missing tests

lint:
	ruff check .
	ruff format --check .
	mypy

format:
	ruff check --fix .
	ruff format .

install-hooks:
	pre-commit install -f --install-hooks

venv:
	python -m venv virtualenv_run
	virtualenv_run/bin/pip install -U pip
	virtualenv_run/bin/pip install -e '.[dev,macho]'

clean:
	rm -rf build/ dist/ *.egg-info/ .tox/ virtualenv_run/ .mypy_cache/ .ruff_cache/ .pytest_cache/ coverage-html/
	find . -name '*.pyc' -delete
	find . -name '__pycache__' -delete

.PHONY: all test lint format venv clean install-hooks
