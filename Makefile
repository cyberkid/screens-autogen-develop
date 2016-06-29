#!/usr/bin/env bash

# ~/.virtualenvs is a typical Python default location
ifndef VENV_PATH
	VENV_PATH=~/.virtualenvs/screen
endif

VENV_ACTIVATE = . $(VENV_PATH)/bin/activate

SRC_ROOT = src

clean:
	find . -name "*.pyc" -print -delete
	rm -rfv $(VENV_PATH)

virtualenv:
	test -d $(VENV_PATH)/bin || virtualenv $(VENV_PATH) --python="$(VIRTUALENV_PYTHON)"
	$(VENV_ACTIVATE) && python setup.py --quiet develop

check:
	$(MAKE) virtualenv
	$(MAKE) pep8 nosetests jasmine

pep8:
	@echo "Running pep8..."
	$(VENV_ACTIVATE) && pep8 src

jasmine:
	@echo "Generating jasmine output..."
	$(VENV_ACTIVATE) && cd $(SRC_ROOT) && \
	SCREEN_CONFIG=test python -m test.web.jasmine

nosetests:
	@echo "Running unit tests..."
	$(VENV_ACTIVATE) && cd $(SRC_ROOT) && \
	PYTHONPATH=. SCREEN_CONFIG=test nosetests test

VERSION := $(shell python setup.py -V)
REPO_URL := $(shell python setup.py --url)

GIT_COMMIT := $(shell git log -n1 --pretty=format:%H ) || /bin/true
