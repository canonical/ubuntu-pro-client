# Unit Testing

Before proceeding with the unit tests, please ensure you have completed the setup instructions in the [Getting Started Tutorial](../tutorials/getting-started.md). This guide covers essential setup information required to run the tests.

All unit and lint tests are run using `tox`, with different versions of Python with specific constraints. We also use `tox-setuptools-version` to specify the correct setuptools version based on what is present in each release, and `tox-pyenv` to recognize the different local [pyenv interpreters](https://github.com/pyenv/pyenv).

First, run the script to install and configure `pyenv`, and the `tox` dependencies:

```shell
./tools/setup_pyenv.sh
```

After that you need to [set up your shell environment](https://github.com/pyenv/pyenv#set-up-your-shell-environment-for-pyenv), according to the pyenv documentation.
The guide has quick snippets to configure `bash`, `zsh` and `fish` shells.

Refresh your terminal to make sure pyenv is working. Then you can run the unit and lint tests:

```shell
tox
```

If you want to just run unit tests, you can specify the test environment:

```shell
tox -e test
```

Or if you want to run a specific test file, you can do so by specifying the test file:

```shell
tox -e test -- uaclient/tests/test_actions.py
```

> **Note**
> There are a number of `autouse` mocks in our unit tests. These are intended to prevent accidental side effects on the host system from running the unit tests, as well as prevent leaks of the system environment into the unit tests.
> One such `autouse` mock tells the unit tests that they are run as root (unless the mock is overriden for a particular test).
> These `autouse` mocks have helped, but may not be preventing all side effects or environment leakage.

The client also includes built-in dep8 tests. These are run as follows:

```shell
autopkgtest -U --shell-fail . -- lxd ubuntu:xenial
```
