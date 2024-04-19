# Testing
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

> **Note**
> There are a number of `autouse` mocks in our unit tests. These are intended to prevent accidental side effects on the host system from running the unit tests, as well as prevent leaks of the system environment into the unit tests.
> One such `autouse` mock tells the unit tests that they are run as root (unless the mock is overriden for a particular test).
> These `autouse` mocks have helped, but may not be preventing all side effects or environment leakage.

The client also includes built-in dep8 tests. These are run as follows:

```shell
autopkgtest -U --shell-fail . -- lxd ubuntu:xenial
```

## Integration Tests

Ubuntu Pro Client uses [behave](https://behave.readthedocs.io)
for its integration testing.

The integration test definitions are stored in the `features/`
directory and consist of two parts: `.feature` files that define the
tests we want to run, and `.py` files which implement the underlying
logic for those tests.

By default, integration tests will do the following on a given cloud platform:
 * Launch an instance running latest daily image of the target Ubuntu release
 * Add the Ubuntu Pro client daily build PPA: [ppa:ua-client/daily](https://code.launchpad.net/~ua-client/+archive/ubuntu/daily)
 * Install the appropriate ubuntu-advantage-tools and ubuntu-advantage-pro deb
 * Run the integration tests on that instance.

The testing can be overridden to install ubuntu-advantage-tools from other sources instead of the daily PPA by providing `UACLIENT_BEHAVE_INSTALL_FROM` to the behave test runner. The default is `UACLIENT_BEHAVE_INSTALL_FROM=daily`, and the other available options are:

- `staging`: install from the [staging PPA](https://code.launchpad.net/~ua-client/+archive/ubuntu/staging)
- `stable`: install from the [stable PPA](https://code.launchpad.net/~ua-client/+archive/ubuntu/stable)
- `archive`: install the latest version available in the archive, not adding any PPA
- `proposed`: install the package from the -proposed pocket - specially useful for SRU testing (see [the release guide](how_to_release_a_new_version_of_ua.md))
- `custom`: install from a custom provided PPA. If set, then two other variables need to be set: `UACLIENT_BEHAVE_CUSTOM_PPA=<PPA URL>` and `UACLIENT_BEHAVE_CUSTOM_PPA_KEYID=<signing key for the PPA>`.
- `local`: install from a local copy of the ubuntu-pro-client source code

`local` is particularly useful, as it runs the suite against the local code, thus including and validating the latest changes made. It is advised to run any related integration tests against local code changes before pushing them to be reviewed.

> **Note**
> Note that we cache the source when running with `UACLIENT_BEHAVE_INSTALL_FROM=local` based on a hash, calculated from the repository state. If you change the python code locally and run the behave tests against your new version, there will be new debs in the cache source with the new repo state hash.

To run the integration tests, use the `tox` command as shown below. 
Please note that, as shown here without arguments, this command would execute all the integration tests sequentially and would take an inordinate amount of time to complete. Always pass arguments to this command to specify a subset of tests to run, as demonstrated next.

```shell
tox -e behave
```

or, if you just want to run a specific file, or a test within a file:

```shell
tox -e behave features/unattached_commands.feature
tox -e behave features/unattached_commands.feature:28
```

or, if you want to run a specific file for a specific release and machine type, or a specific test:

```shell
tox -e behave -- features/config.feature -D releases=jammy -D machine_types=lxd-container
tox -e behave -- features/config.feature:132 -D releases=jammy -D machine_types=lxd-vm
```

As can be seen, this will run behave tests for only the release 22.04 (Jammy Jellyfish). Similary the behave tests can be run for all supported releases, including LTS releases under ESM, and the development release at some point in the development cycle. Please note that the specific release versions may change over time, so it's recommended to refer to the documentation for the latest information.

Furthermore, when developing/debugging a new scenario:

 1. Add a `@wip` tag decorator on the scenario
 2. To only run @wip scenarios run: `tox -e behave -- -w`
 3. If you want to use a debugger:
    1. Add ipdb to integration-requirements.txt
    2. Add ipdb.set_trace() in the code block you wish to debug

(If you're getting started with behave, we recommend at least reading
through [the behave
tutorial](https://behave.readthedocs.io/en/latest/tutorial.html) to get
an idea of how it works, and how tests are written.)

## Integration testing on EC2
The following tox environments allow for testing focal on EC2:

```
  # To test ubuntu-pro-images
  tox -e behave -- -D release=focal -D machine_types=aws.pro
  # To test Canonical cloud images (non-ubuntu-pro)
  tox -e behave -- -D release=focal -D machine_types=aws.generic
```

To run the test for a different release, just update the release version string. For example,
to run AWS pro xenial tests, you can run:

```
tox -e behave -- -D release=xenial -D machine_types=aws.pro
```

In order to run EC2 tests, please set up the [pycloudlib toml
file](https://github.com/canonical/pycloudlib/blob/main/pycloudlib.toml.template) with
the required EC2 credentials.

To specifically run non-ubuntu pro tests using canonical cloud-images an
additional token obtained from https://ubuntu.com/pro needs to be set:
  - UACLIENT_BEHAVE_CONTRACT_TOKEN=<your_token>

* To manually run EC2 integration tests with a specific AMI Id provide the
following environment variable to launch your specific  AMI instead of building
a daily ubuntu-advantage-tools image.
```sh
UACLIENT_BEHAVE_REUSE_IMAGE=your-custom-ami tox -e behave -- -D release=focal -D machine_types=aws.pro
```

## Integration testing on Azure
The following tox environments allow for testing focal on Azure:

```
  # To test ubuntu-pro-images
  tox -e behave -- -D release=focal -D machine_types=aws.pro
  # To test Canonical cloud images (non-ubuntu-pro)
  tox -e behave -- -D release=focal -D machine_types=aws.generic
```

To run the test for a different release, just update the release version string. For example,
to run Azure pro xenial tests, you can run:

```
  tox -e behave -- -D machine_types=azure.pro
```

In order to run Azure tests, please set up the [pycloudlib toml
file](https://github.com/canonical/pycloudlib/blob/main/pycloudlib.toml.template) with
the required Azure credentials.

To specifically run non-ubuntu pro tests using canonical cloud-images an
additional token obtained from https://ubuntu.com/pro needs to be set:
  - UACLIENT_BEHAVE_CONTRACT_TOKEN=<your_token>

* To manually run Azure integration tests with a specific Image Id provide the
following environment variable to launch your specific Image Id instead of building
a daily ubuntu-advantage-tools image.
```sh
UACLIENT_BEHAVE_REUSE_IMAGE=your-custom-image-id tox -e behave -- -D release=focal -D machine_types=azure.pro
```

## Integration testing on GCP
The following tox environments allow for testing focal on GCP:

```
  # To test ubuntu-pro-images
  tox -e behave -- -D release=focal -D machine_types=gcp.pro
  # To test Canonical cloud images (non-ubuntu-pro)
  tox -e behave -- -D release=focal -D machine_types=gcp.generic
```

To run the test for a different release, just update the release version string. For example,
to run GCP pro xenial tests, you can run:

```
tox -e behave -- -D release=xenial machine_types=gcp.pro
```

In order to run GCP tests, please set up the [pycloudlib toml
file](https://github.com/canonical/pycloudlib/blob/main/pycloudlib.toml.template) with
the required GCP credentials.

To specifically run non-ubuntu pro tests using canonical cloud-images an
additional token obtained from https://ubuntu.com/pro needs to be set:
  - UACLIENT_BEHAVE_CONTRACT_TOKEN=<your_token>

* To manually run GCP integration tests with a specific Image Id provide the
following environment variable to launch your specific Image Id instead of building
a daily ubuntu-advantage-tools image.
```sh
UACLIENT_BEHAVE_REUSE_IMAGE=your-custom-image-id tox -e behave -- -D release=focal -D machine_types=gcp.pro
```