

build:
	@echo Nothing to be done for build

deps:
	./dev/read-dependencies -v 3 --system-pkg-names --test-distro

clean:
	rm -f ubuntu-advantage-tools*gz
	find . -type f -name '*.pyc' -delete
	rm -rf .tox
	find . -type d -name '*__pycache__' -delete

deb:
	@echo Building unsigned debian package
	@which dpkg-buildpackage || \
               { echo -e "Missing build dependencies. Install with:" \
                 "\n make ci-deps"; exit 1; }
	./dev/bddeb

test:
	@tox


.PHONY: build deps clean deb test
