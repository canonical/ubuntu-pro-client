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
	pip install tox


.PHONY: build clean test testdeps demo
