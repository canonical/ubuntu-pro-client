build:
	@echo Nothing to build.

test:
	@tox -e python

lint:
	@tox -e lint
	@shellcheck -s dash ubuntu-advantage update-motd.d/*


.PHONY: build test lint
