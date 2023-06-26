VENV          	= .sphinx/venv
ACTIVATE_VENV	= $(VENV)/bin/activate
SOURCEDIR     	= docs/
BUILDDIR     	= docs/build/

install:
	python3 -m venv $(VENV)
	. $(ACTIVATE_VENV); pip install --upgrade -r docs-requirements.txt

build:
	. $(ACTIVATE_VENV); sphinx-build -W -b html $(SOURCEDIR) $(BUILDDIR)

run:
	. $(ACTIVATE_VENV); sphinx-autobuild $(SOURCEDIR) $(BUILDDIR)

serve:
	python3 -m http.server --directory $(BUILDDIR) 8000

clean:
	rm -rf $(VENV)
	rm -rf $(BUILDDIR)

.PHONY: install build run serve clean
