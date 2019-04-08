# Ubuntu Advantage Client

[![Build Status](https://travis-ci.org/CanonicalLtd/ubuntu-advantage-client.svg?branch=master)](https://travis-ci.org/CanonicalLtd/ubuntu-advantage-client)

The Ubuntu Advantage client provides users with a simple mechanism to
view, enable, and disable offerings from Canonical on their system. The
following entitlements are supported:

- [Ubuntu Extended Security Maintenance](https://ubuntu.com/esm)
- [Livepatch Service](https://www.ubuntu.com/livepatch)
- FIPS 140-2 Certified Modules
- FIPS 140-2 Non-Certified Module Updates
- Common Criteria EAL2 certification artifacts provisioning

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

To build the Ubuntu Advantage Client package users

```shell
make deb
```

## Daily Builds

On Launchpad, there is a [daily build recipe](https://code.launchpad.net/~canonical-server/+recipe/ua-client-daily),
which will build the client and place it in the [ua-client-daily PPA](https://code.launchpad.net/~canonical-server/+archive/ubuntu/ua-client-daily).

## Demo

Users can demo the client with a local backend. This can be done with
the following:

```shell
# Set up ua-contracts in a docker container and two clients
./demo/demo-contract-service CanonicalLtd go
./demo/run-uaclient --series disco
./demo/run-uaclient --series xenial -b multipass
```
