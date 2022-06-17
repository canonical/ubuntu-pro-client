mkfile_path := $(abspath $(lastword $(MAKEFILE_LIST)))
mkfile_dir := $(dir $(mkfile_path))

build:
	$(MAKE) -C apt-hook build

clean:
	rm -f *.build *.buildinfo *.changes .coverage *.deb *.dsc *.tar.gz *.tar.xz
	rm -f azure-*-uaclient-ci-* ec2-uaclient-ci-* gcp-*-uaclient-ci-* lxd-container-*-uaclient-ci-* lxd-virtual-machine-*-uaclient-ci-*
	rm -rf *.egg-info/ .tox/ .cache/ .mypy_cache/
	rm -rf docs/build/
	find . -type f -name '*.pyc' -delete
	find . -type d -name '*__pycache__' -delete
	$(MAKE) -C apt-hook clean

deps:
	@which mk-build-deps > /dev/null || { \
		echo "Missing mk-build-deps; installing devscripts, equivs."; \
		apt-get install --no-install-recommends --yes devscripts equivs; \
	}
	mk-build-deps --tool "apt-get --no-install-recommends --yes" \
		--install --remove ${mkfile_dir}/debian/control

test:
	@tox

.PHONY: build clean test
