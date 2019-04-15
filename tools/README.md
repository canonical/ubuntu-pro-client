# Tools

The 'tools' directory is reserved for test tools and scripts. Nothing
in this directory will be shipped as part of the packaging

## Files

- bddeb: used to build test debs
- changelog.in: template for change log, used by bddeb
- constraints-bionic: Bionic versions of packages used by Tox
- constraints-trusty: Trusty versions of packages used by Tox
- constraints-xenial: Xenial versions of packages used by Tox
- control.in: template for control file, used by bddeb
- make-tarball: create a upstream tarball
- pkg-deps.json: translates pip dependencies to distro packages
- read-dependencies: reads and installs dependencies for build and test
