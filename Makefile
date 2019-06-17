build:
	$(MAKE) -C apt-hook build

clean:
	rm -f *.build *.buildinfo *.changes .coverage *.deb *.dsc *.tar.gz *.tar.xz
	rm -rf *.egg-info/ .tox/ .cache/
	find . -type f -name '*.pyc' -delete
	find . -type d -name '*__pycache__' -delete
	$(MAKE) -C apt-hook clean

test:
	@tox

demo:
	@echo Creating contract-bionic-demo container with ua-contracts server
	@./demo/demo-contract-service

testdeps:
	pip install tox


.PHONY: build clean test testdeps demo
