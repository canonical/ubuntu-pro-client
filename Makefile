build:
	@echo Nothing to build.

test:
	@tox

lint:
	@shellcheck -s dash ubuntu-advantage update-motd.d/*


.PHONY: build test lint
