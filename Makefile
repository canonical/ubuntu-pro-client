build:
	@echo Nothing to build.

testdep:
	pip install tox

test:
	@tox -e python

lint:
	@tox -e lint
	@shellcheck -s dash ubuntu-advantage modules/* update-motd.d/*


.PHONY: build testdep test lint
