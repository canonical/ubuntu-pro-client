

build:
	$(MAKE) -C apt-hook build

deps:
	./tools/read-dependencies -v 3 --system-pkg-names --test-distro

clean:
	rm -f *.build *.buildinfo *.changes .coverage *.deb *.dsc *.tar.gz
	rm -rf *.egg-info/ .tox/ .cache/
	find . -type f -name '*.pyc' -delete
	find . -type d -name '*__pycache__' -delete

deb:
	@echo Building unsigned debian package
	@which dpkg-buildpackage || \
               { echo -e "Missing build dependencies. Install with:" \
                 "\n make deps"; exit 1; }
	./tools/bddeb

test:
	@tox

testdeps:
	pip install tox


.PHONY: build deps clean deb test testdeps
