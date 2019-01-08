# ubuntu-advantage tool

[![Build Status](https://travis-ci.org/CanonicalLtd/ubuntu-advantage-script.svg?branch=master)](https://travis-ci.org/CanonicalLtd/ubuntu-advantage-script)

This tool is used to enable or disable specific Ubuntu Advantage offerings from Canonical. Version 18.1 or later is a python-based client which talks to a
UA Contract backend service API to navigate UA contracts, entitlement details
and status.

Currently it supports setup and maintenance of the following entitlements:

- [Ubuntu Extended Security Maintenance](https://ubuntu.com/esm) archive.
- [Canonical Livepatch](https://www.ubuntu.com/server/livepatch) service for managed live kernel patching.
- Canonical FIPS 140-2 Certified Modules. Install Configure and Enable FIPS modules.
- Canonical Common Criteria EAL2 certification artifacts provisioning

Run

``
$ [sudo] python -m uaclient.cli --help
```

to display usage information.


## Testing

System tests and tests lint:

```
$ tox
```

Lint:

```
$ tox -e lint

Style:

```
$ tox -e pycodestyle
```

Build package:
```
$ make deb
OR
$ dpkg-buildpackage -us -uc
```

Dep8 Tests:

```
# To test on 16.04:
$ autopkgtest --shell-fail . -- lxd ubuntu:xenial
```


Setup Contract Service API with sample data:
```
# Launch a bionic container to host your Contact service with sample data
make demo

# Create a deb based on python version of ubuntu-advatange-tools
make deb

# Create a vm or container running the python uaclient
$ PYTHONPATH=. ./dev/run-uaclient --series disco --backend multipass

# play with uaclient on your local dev system
$ sudo UA_CONFIG_FILE=uaclient-devel.conf python -m uaclient.cli
```



### Disclaimer
The python implementation of this ubuntu-advantage-tools will replace the original shell scripts
under modules/. They have been left in this branch until a final release of ubuntu-advantage-tools has been SRU'd.
After that point, all shell functions and methods will be dropped from this repository.
