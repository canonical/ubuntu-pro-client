

build:
	@echo Nothing to be done for build

deps:
	./dev/read-dependencies -v 3 --system-pkg-names --test-distro

clean:
	rm -f *.build *.buildinfo *.changes .coverage *.deb *.dsc *.tar.gz
	rm -rf *.egg-info/ .tox/
	find . -type f -name '*.pyc' -delete
	find . -type d -name '*__pycache__' -delete

deb:
	@echo Building unsigned debian package
	@which dpkg-buildpackage || \
               { echo -e "Missing build dependencies. Install with:" \
                 "\n make ci-deps"; exit 1; }
	./dev/bddeb

test:
	@tox

testdeps:
	pip install tox


.PHONY: build deps clean deb test testdeps
