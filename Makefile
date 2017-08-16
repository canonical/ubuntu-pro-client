test:
	@tox

lint:
	@shellcheck -s dash ubuntu-advantage update-motd.d/*


.PHONY: test lint
