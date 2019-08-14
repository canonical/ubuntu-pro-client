# Ubuntu Advantage Client

[![Build Status](https://travis-ci.org/CanonicalLtd/ubuntu-advantage-client.svg?branch=master)](https://travis-ci.org/CanonicalLtd/ubuntu-advantage-client)

The Ubuntu Advantage client provides users with a simple mechanism to
view, enable, and disable offerings from Canonical on their system. The
following entitlements are supported:

- [Common Criteria EAL2 certification artifacts provisioning](https://ubuntu.com/cc-eal)
- [Canonical CIS Benchmark Audit Tool](https://ubuntu.com/cis)
- [Ubuntu Extended Security Maintenance](https://ubuntu.com/esm)
- [FIPS 140-2 Certified Modules](https://ubuntu.com/fips)
- [FIPS 140-2 Non-Certified Module Updates](https://ubuntu.com/fips-updates)
- [Livepatch Service](https://www.ubuntu.com/livepatch)

## Obtaining the Client

The client comes pre-installed on all Ubuntu systems. Users can run the
`ua` command to learn more or view the manpage.

## Testing

All unit and lint tests are run using tox:

```shell
tox
```

The client also includes built-in dep8 tests. These are run as follows:

```shell
autopkgtest -U --shell-fail . -- lxd ubuntu:xenial
```

## Building

The packaging for the UA client package (ubuntu-advantage-tools) is
in-tree, so you can build the package the way you would normally build
a Debian package:

```shell
dpkg-buildpackage
```

or, if you want to build for a target release other than the release
you're on, [configure sbuild](https://wiki.ubuntu.com/SimpleSbuild) and
use that for the build:

```shell
debuild -S
sbuild --dist=<target> ../ubuntu-advantage-tools_*.dsc
```

## Code Formatting

The `ubuntu-advantage-client` code base is formatted using
[black](https://github.com/psf/black).  When making changes, you should
ensure that your code is blackened, or it will be rejected by CI.
Formatting the whole codebase is as simple as running:

```shell
black uaclient/
```

To make it easier to avoid committing incorrectly formatted code, this
repo includes configuration for [pre-commit](https://pre-commit.com/)
which will stop you from committing any code that isn't blackened.  To
install the project's pre-commit hook, install `pre-commit` and run:

```shell
pre-commit install
```

(To install `black` and `pre-commit` at the appropriate versions for
the project, you should install them via `dev-requirements.txt`.)

## Daily Builds

On Launchpad, there is a [daily build recipe](https://code.launchpad.net/~canonical-server/+recipe/ua-client-daily),
which will build the client and place it in the [ua-client-daily PPA](https://code.launchpad.net/~canonical-server/+archive/ubuntu/ua-client-daily).

## Demo

Users can demo the client with a local backend. This can be done with
the following:

```shell
# Set up ua-contracts in a docker container in a bionic lxc on port 3000
make demo
# Set up two clients pointing at the local contract server
./demo/run-uaclient --series disco
./demo/run-uaclient --series xenial -b multipass
```
