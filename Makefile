build:
	@echo Nothing to build.

test:
	@tox

lint:
	@shellcheck -s dash advantage update-motd.d/*


.PHONY: build test lint
