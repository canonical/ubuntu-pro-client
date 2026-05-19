# Unit Testing

Before proceeding with unit tests, ensure you have completed the setup
instructions in the [Getting Started Tutorial](../tutorial/getting-started.md).
This guide covers essential setup information required to run the tests.

## Using Workshop (recommended)

If you have [Canonical Workshop](https://canonical-workshop.readthedocs-hosted.com/)
installed, running the unit tests is as simple as:

```shell
workshop test
```

To run a specific test file:

```shell
workshop test -- uaclient/tests/test_actions.py
```

Workshop handles the Python toolchain automatically, so no additional setup is
needed.

## Using tox directly (alternative)

First install the necessary package dependencies via the Makefile:

```shell
sudo apt install make
sudo make deps
```

Then run the unit and lint tests:

```shell
tox
```

If you want to just run unit tests, you can specify the test environment:

```shell
tox -e test
```

Or to run a specific test file, you can specify the test file:

```shell
tox -e test -- uaclient/tests/test_actions.py
```

> **Note**
> There are a number of `autouse` mocks in our unit tests. These are intended
> to prevent accidental side effects on the host system from running the unit
> tests, as well as prevent leaks of the system environment into the unit tests.
> One such `autouse` mock tells the unit tests that they are run as root (unless
> the mock is overriden for a particular test).
> These `autouse` mocks have helped, but may not fully prevent all side effects
> or environment leakage.

The client also includes built-in dep8 tests. These are run as follows:

```shell
autopkgtest -U --shell-fail . -- lxd ubuntu:xenial
```
