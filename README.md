# ubuntu-advantage tool

[![Build Status](https://travis-ci.org/CanonicalLtd/ubuntu-advantage-script.svg?branch=master)](https://travis-ci.org/CanonicalLtd/ubuntu-advantage-script)

This tool is used to enable or disable specific Ubuntu Advantage offerings from Canonical.

Currently it supports the following:

- [Ubuntu Extended Security Maintenance](https://ubuntu.com/esm) archive.
- [Canonical Livepatch](https://www.ubuntu.com/server/livepatch) service for managed live kernel patching.
- [Canonical FIPS 140-2 Certified Modules] Install Configure and Enable FIPS modules.

Run 

```
$ ./ubuntu-advantage
```

to display usage information.


## Testing

System tests and tests lint:

```
$ make test
```

Lint:

```
$ make lint
```

Dep8 Tests:

```
# To test on 16.04:
$ autopkgtest --shell-fail . -- lxd ubuntu:xenial
```
