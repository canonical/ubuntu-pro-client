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
# Launch a bionic container to host your Contact service
$ lxc launch ubuntu-daily:bionic contract-api
$ lxc exec contract-api bash

# Grab openapi-generator script from  https://github.com/OpenAPITools/openapi-generator#launcher-script
# Place openapi-generator in your PATH
<contract-api> $ git clone git@github.com:CanonicalLtd/ua-service.git
<contract-api> $ cd ua-service/contracts
<contract-api> $ apt-install openjdk-11-jdk-headless
# Download and install latest maven https://maven.apache.org/download.cgi

# Generate a default openapi python server
<contract-api> $ ./scripts/generate-python-server.bash
# Install openapi server deps
<contract-api> $ pip3 install -r requirements.txt
# Patch default_controller.py with sample response content.
# Run the openapiserver in your container
<contract-api> $ python3 -m openapi_server

# Edit uaclient-devel.conf with contract-api ipaddress
$ lxc list contract-api -c 4 | grep 10 | awk '{print $2}'
$ vi uaclient-devel.conf

# play with uaclient on your local dev system
$ sudo UA_CONFIG_FILE=uaclient-devel.conf python -m uaclient.cli
```
