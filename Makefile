mkfile_path := $(abspath $(lastword $(MAKEFILE_LIST)))
mkfile_dir := $(dir $(mkfile_path))

build:
	$(MAKE) -C apt-hook build

clean:
	rm -f *.build *.buildinfo *.changes .coverage *.deb *.dsc *.tar.gz *.tar.xz
	rm -rf *.egg-info/ .tox/ .cache/ .mypy_cache/
	find . -type f -name '*.pyc' -delete
	find . -type d -name '*__pycache__' -delete
	$(MAKE) -C apt-hook clean

demo:
	@echo Creating contract-bionic-demo container with ua-contracts server
	@./demo/demo-contract-service

deps:
	@which mk-build-deps > /dev/null || { \
		echo "Missing mk-build-deps; installing devscripts, equivs."; \
		apt-get install --no-install-recommends --yes devscripts equivs; \
	}
	mk-build-deps --tool "apt-get --no-install-recommends --yes" \
		--install --remove ${mkfile_dir}/debian/control

test:
	@tox

testdeps:
	pip install -U tox

travis-deb-install:
	git fetch --unshallow
	sudo apt-get update
	sudo apt-get build-dep -y ubuntu-advantage-tools
	sudo apt-get install -y --install-recommends sbuild ubuntu-dev-tools dh-systemd
	# Missing build-deps
	sudo apt-get install -y --install-recommends libapt-pkg-dev python3-mock python3-pytest

# Use the mirror for a GCE region, to speed things up. (Travis build VMs use
# DataSourceNone so we can't dynamically determine the correct region.)
travis-deb-script: export DEBOOTSTRAP_MIRROR=http://us-central1.gce.archive.ubuntu.com/ubuntu/
travis-deb-script:
	debuild -S -uc -us
	sudo sbuild-adduser ${USER}
	cp /usr/share/doc/sbuild/examples/example.sbuildrc /home/${USER}/.sbuildrc
	# Use this to get a new shell where we're in the sbuild group
	sudo -E su ${USER} -c 'mk-sbuild ${PACKAGE_BUILD_SERIES}'
	sudo -E su ${USER} -c 'sbuild --nolog --verbose --dist=${PACKAGE_BUILD_SERIES} ../ubuntu-advantage-tools*.dsc'


.PHONY: build clean test testdeps demo
