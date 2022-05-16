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

The client also includes built-in dep8 tests. These are run as follows:

```shell
autopkgtest -U --shell-fail . -- lxd ubuntu:xenial
```

## Integration Tests

ubuntu-advantage-client uses [behave](https://behave.readthedocs.io)
for its integration testing.

The integration test definitions are stored in the `features/`
directory and consist of two parts: `.feature` files that define the
tests we want to run, and `.py` files which implement the underlying
logic for those tests.

By default, integration tests will do the following on a given cloud platform:
 * Launch an instance running latest daily image of the target Ubuntu release
 * Add the Ubuntu advantage client daily build PPA: [ppa:ua-client/daily](https://code.launchpad.net/~ua-client/+archive/ubuntu/daily)
 * Install the appropriate ubuntu-advantage-tools and ubuntu-advantage-pro deb
 * Run the integration tests on that instance.

The testing can be overridden to run using a local copy of the ubuntu-advantage-client source code instead of the daily PPA by providing the following environment variable to the behave test runner:
```UACLIENT_BEHAVE_BUILD_PR=1```

> Note that, by default, we cache the source even when `UACLIENT_BEHAVE_BUILD_PR=1`. This means that if you change the python code locally and want to run the behave tests against your new version, you need to either delete the cache (`rm /tmp/uaclient_behave`) or also set `UACLIENT_BEHAVE_CACHE_SOURCE=0`.

To run the tests, you can use `tox`:

```shell
tox -e behave-lxd-20.04
```

or, if you just want to run a specific file, or a test within a file:

```shell
tox -e behave-lxd-20.04 features/unattached_commands.feature
tox -e behave-lxd-20.04 features/unattached_commands.feature:55
```

As can be seen, this will run behave tests only for release 20.04 (Focal Fossa). We are currently
supporting 5 distinct releases:

* 22.04 (Jammy Jellyfish)
* 21.10 (Impish Indri)
* 20.04 (Focal Fossa)
* 18.04 (Bionic Beaver)
* 16.04 (Xenial Xerus)

Therefore, to change which release to run the behave tests against, just change the release version
on the behave command.

Furthermore, when developing/debugging a new scenario:

 1. Add a `@wip` tag decorator on the scenario
 2. To only run @wip scenarios run: `tox -e behave-lxd-20.04 -- -w`
 3. If you want to use a debugger:
    1. Add ipdb to integration-requirements.txt
    2. Add ipdb.set_trace() in the code block you wish to debug

(If you're getting started with behave, we recommend at least reading
through [the behave
tutorial](https://behave.readthedocs.io/en/latest/tutorial.html) to get
an idea of how it works, and how tests are written.)

## Iterating Locally

To make running the tests repeatedly less time-intensive, our behave
testing setup has support for reusing images between runs via two
configuration options (provided in environment variables),
`UACLIENT_BEHAVE_IMAGE_CLEAN` and `UACLIENT_BEHAVE_REUSE_IMAGE`.

To avoid the test framework cleaning up the image it creates, you can
run it like this:

```sh
UACLIENT_BEHAVE_IMAGE_CLEAN=0 tox -e behave
```

which will emit a line like this above the test summary:

```
Image cleanup disabled, not deleting: behave-image-1572443113978755
```

You can then reuse that image by plugging its name into your next test
run, like so:

```sh
UACLIENT_BEHAVE_REUSE_IMAGE=behave-image-1572443113978755 tox -e behave
```

If you've done this correctly, you should see something like
`reuse_image = behave-image-1572443113978755` in the "Config options"
output, and test execution should start immediately (without the usual
image build step).

(Note that this handling is specific to our behave tests as it's
performed in `features/environment.py`, so don't expect to find
documentation about it outside of this codebase.)

For development purposes there is `reuse_container` option.
If you would like to run behave tests in an existing container
you need to add `-D reuse_container=container_name`:

```sh
tox -e behave -D reuse_container=container_name
```

## Optimizing total run time of integration tests with snapshots
When `UACLIENT_BEHAVE_SNAPSHOT_STRATEGY=1` we create a snapshot of an instance
with ubuntu-advantage-tools installed and restore from that snapshot for all tests.
This adds an upfront cost that is amortized across several test scenarios.

Based on some rough testing in July 2021, these are the situations
when you should set UACLIENT_BEHAVE_SNAPSHOT_STRATEGY=1

> At time of writing, starting a lxd.vm instance from a local snapshot takes
> longer than starting a fresh lxd.vm instance and installing ua.

| machine_type  | condition          |
| ------------- | ------------------ |
| lxd.container | num_scenarios > 7  |
| lxd.vm        | never              |
| gcp           | num_scenarios > 5  |
| azure         | num_scenarios > 14 |
| aws           | num_scenarios > 11 |

## Integration testing on EC2
The following tox environments allow for testing focal on EC2:

```
  # To test ubuntu-pro-images
  tox -e behave-awspro-20.04
  # To test Canonical cloud images (non-ubuntu-pro)
  tox -e behave-awsgeneric-20.04
```

To run the test for a different release, just update the release version string. For example,
to run AWS pro xenial tests, you can run:

```
tox -e behave-awspro-16.04
```

In order to run EC2 tests, please set up the [pycloudlib toml
file](https://github.com/canonical/pycloudlib/blob/main/pycloudlib.toml.template) with
the required EC2 credentials.

To specifically run non-ubuntu pro tests using canonical cloud-images an
additional token obtained from https://ubuntu.com/advantage needs to be set:
  - UACLIENT_BEHAVE_CONTRACT_TOKEN=<your_token>

By default, the public AMIs for Ubuntu Pro testing used for each Ubuntu
release are defined in features/aws-ids.yaml. These ami-ids are determined by
running `./tools/refresh-aws-pro-ids`.

Integration tests will read features/aws-ids.yaml to determine which default
AMI id to use for each supported Ubuntu release.

To update `features/aws-ids.yaml`, run `./tools/refresh-aws-pro-ids` and put up
a pull request against this repo to updated that content from the ua-contracts
marketplace definitions.

* To manually run EC2 integration tests with a specific AMI Id provide the
following environment variable to launch your specific  AMI instead of building
a daily ubuntu-advantage-tools image.
```sh
UACLIENT_BEHAVE_REUSE_IMAGE=your-custom-ami tox -e behave-awspro-20.04
```

## Integration testing on Azure
The following tox environments allow for testing focal on Azure:

```
  # To test ubuntu-pro-images
  tox -e behave-azurepro-20.04
  # To test Canonical cloud images (non-ubuntu-pro)
  tox -e behave-azuregeneric-20.04
```

To run the test for a different release, just update the release version string. For example,
to run Azure pro xenial tests, you can run:

```
tox -e behave-azurepro-16.04
```

In order to run Azure tests, please set up the [pycloudlib toml
file](https://github.com/canonical/pycloudlib/blob/main/pycloudlib.toml.template) with
the required Azure credentials.

To specifically run non-ubuntu pro tests using canonical cloud-images an
additional token obtained from https://ubuntu.com/advantage needs to be set:
  - UACLIENT_BEHAVE_CONTRACT_TOKEN=<your_token>

* To manually run Azure integration tests with a specific Image Id provide the
following environment variable to launch your specific Image Id instead of building
a daily ubuntu-advantage-tools image.
```sh
UACLIENT_BEHAVE_REUSE_IMAGE=your-custom-image-id tox -e behave-azurepro-20.04
```

## Integration testing on GCP
The following tox environments allow for testing focal on GCP:

```
  # To test ubuntu-pro-images
  tox -e behave-gcppro-20.04
  # To test Canonical cloud images (non-ubuntu-pro)
  tox -e behave-gcpgeneric-20.04
```

To run the test for a different release, just update the release version string. For example,
to run GCP pro xenial tests, you can run:

```
tox -e behave-gcppro-16.04
```

In order to run GCP tests, please set up the [pycloudlib toml
file](https://github.com/canonical/pycloudlib/blob/main/pycloudlib.toml.template) with
the required GCP credentials.

To specifically run non-ubuntu pro tests using canonical cloud-images an
additional token obtained from https://ubuntu.com/advantage needs to be set:
  - UACLIENT_BEHAVE_CONTRACT_TOKEN=<your_token>

* To manually run GCP integration tests with a specific Image Id provide the
following environment variable to launch your specific Image Id instead of building
a daily ubuntu-advantage-tools image.
```sh
UACLIENT_BEHAVE_REUSE_IMAGE=your-custom-image-id tox -e behave-gcppro-20.04
```
