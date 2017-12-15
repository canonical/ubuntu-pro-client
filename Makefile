UA_SCRIPTS = ubuntu-advantage $(wildcard modules/*)
MOTD_SCRIPTS = $(wildcard update-motd.d/*)


build:
	@echo Nothing to build.

testdep:
	pip install tox

test:
	@tox -e python

lint: lint-py lint-sh

lint/docker: lint-py lint-sh/docker

lint-py:
	@tox -e lint

lint-sh: SHELLCHECK = shellcheck
lint-sh: BASH_SCRIPTS = $(UA_SCRIPTS)
lint-sh: DASH_SCRIPTS = $(MOTD_SCRIPTS)
lint-sh: _lint-sh-command

lint-sh/docker: SHELLCHECK = docker run --rm -it -v $(PWD):/repo koalaman/shellcheck
lint-sh/docker: BASH_SCRIPTS = $(patsubst %,/repo/%,$(UA_SCRIPTS))
lint-sh/docker: DASH_SCRIPTS = $(patsubst %,/repo/%,$(MOTD_SCRIPTS))
lint-sh/docker: _lint-sh-command

_lint-sh-command:
	@$(SHELLCHECK) -s bash $(BASH_SCRIPTS)
	@$(SHELLCHECK) -s dash $(DASH_SCRIPTS)

.PHONY: build testdep test lint lint/docker lint-py lint-sh lint-sh/docker _lint-sh-command
