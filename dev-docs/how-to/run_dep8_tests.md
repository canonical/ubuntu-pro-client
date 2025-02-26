# How to run dep8 tests

The ubuntu-advantage-tools source package currently supports [dep8
tests]( https://salsa.debian.org/ci-team/autopkgtest/-/blob/master/doc/README.package-tests.rst).
Those dep8 tests can be found under `debian/tests/usage` and although they are currently only
running a few Pro client commands, the idea is to verify if any modification to our package dependencies
will affect the Pro client.

Right now, we are looking for signal from our `python3-apt` dependency. That's why we are running
the `packages` API there, as those endpoints directly interact with APT.

If you perform any modification to those tests, you can verify it by following these steps:

1. Install the `autopkgtest` application:

```shell
sudo apt install autopkgtest
```

2. Run the following command:

```shell
autopkgtest -U --shell-fail . -- lxd ubuntu:xenial
```

Note that you can run this command on any release we support, not only Xenial,
and it will run for all releases by launchpad when dependencies are updated.
