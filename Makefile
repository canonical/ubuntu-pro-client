UA_SCRIPTS = ubuntu-advantage $(wildcard modules/*)
MOTD_SCRIPTS = $(wildcard update-motd.d/*)


build:
	@echo Nothing to be done for build

deb-trusty:
	# TODO provide proper py2 py3 package build script
	@echo Building unsigned debian package for trusty
	patch -p1 -i dev/trusty-deb.patch
	@which dpkg-buildpackage || \
               { echo -e "Missing build dependencies. Install with:" \
                 "\n sudo apt-get install devscripts"; exit 1; }
	dpkg-buildpackage -us -uc
	patch -p1 -R -i dev/trusty-deb.patch

deb:
	@echo Building unsigned debian package
	@which dpkg-buildpackage || \
               { echo -e "Missing build dependencies. Install with:" \
                 "\n sudo apt-get install devscripts"; exit 1; }
	dpkg-buildpackage -us -uc


demo: deb
	@echo Cloning ua-service repo and building a python openapi service
	./dev/demo-contract-service

testdep:
	pip install tox

test:
	@tox

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

clean:
	rm -f ubuntu-advantage-tools*gz
	find . -type f -name '*.pyc' -delete
	rm -rf .tox
	find . -type d -name '*__pycache__' -delete

.PHONY: build deb demo testdep test lint lint/docker lint-py lint-sh lint-sh/docker _lint-sh-command clean
