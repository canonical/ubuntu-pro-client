build:
	@echo Nothing to build.

testdep:
	pip install tox

test:
	@tox -e python

lint: lint-py lint-sh

lint-py:
	@tox -e lint

lint-sh:
	@shellcheck -s bash ubuntu-advantage modules/*
	@shellcheck -s dash update-motd.d/*


.PHONY: build testdep test lint lint-py lint-sh
