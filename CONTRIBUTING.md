# Contributing to Ubuntu Advantage Client

## Architecture
Ubuntu Advantage client, hereafter "UA client", is a python3-based command line
utility. It provides a CLI to attach, detach, enable,
disable and check status of support related services.

The package `ubuntu-advantage-tools` also provides a C++ APT hook which helps
advertise ESM service and available packages in MOTD and during various apt
commands.

The `ubuntu-advantage-pro` package delivers auto-attach auto-enable
functionality via init scripts and systemd services for various cloud
platforms.

By default, Ubuntu machines are deployed in an unattached state. A machine can
get manually or automatically attached to a specific contract by interacting
with the Contract Server REST API. Any change in state of services or machine
attach results in additional interactions with the Contract Server API to
validate such operations.

### Attaching a machine
Each Ubuntu SSO account holder has access to one or more contracts. To attach
a machine to an Ubuntu Advantage contract:

* An Ubuntu SSO account holder must obtain a contract token from
https://ubuntu.com/advantage.
* Run `sudo ua attach <contractToken>` on the machine
  - Ubuntu Pro images for AWS, Azure and GCP perform an auto-attach without tokens
* UA Client reads config from /etc/ubuntu-advantage/uaclient.conf to obtain
  the contract_url (default: https://contracts.canonical.com)
* UA Client POSTs to the Contract Server API @
  <contract_url>/api/v1/context/machines/token providing the \<contractToken\>
* The Contract Server responds with a JSON blob containing an unique machine
  token, service credentials, affordances, directives and obligations to allow
  enabling and disabling Ubuntu Advantage services
* UA client writes the machine token API response to the root-readonly
  /var/lib/ubuntu-advantage/private/machine-token.json
* UA client auto-enables any services defined with
  `obligations:{enableByDefault: true}`

#### Attaching with --attach-config
Running `ua attach` with the `--attach-config` may be better suited to certain scenarios.

When using `--attach-config` the token must be passed in the file rather than on the command line. This is useful in situations where it is preffered to keep the secret token in a file.

Optionally, the attach config file can be used to override the services that are automatically enabled as a part of the attach process.

An attach config file looks like this:
```yaml
token: YOUR_TOKEN_HERE  # required
enable_services:        # optional list of service names to auto-enable
  - esm-infra
  - esm-apps
  - cis
```

And can be passed on the cli like this:
```shell
sudo ua attach --attach-config /path/to/file.yaml
```

### Enabling a service
Each service controlled by UA client will have a python module in
uaclient/entitlements/\*.py which handles setup and teardown of services when
enabled or disabled.

If a contract entitles a machine to a service, `root` user can enable the
service with `ua enable <service>`.  If a service can be disabled
`ua disable <service>` will be permitted.

The goal of the UA client is to remain simple and flexible and let the
contracts backend drive dynamic changes in contract offerings and constraints.
In pursuit of that goal, the UA client obtains most of it's service constraints
from a machine token that it obtains from the Contract Server API.

The UA Client is simple in that it relies on the machine token on the attached
machine to describe whether a service is applicable for an environment and what
configuration is required to properly enable that service.

Any interactions with the Contract server API are defined as UAContractClient
class methods in [uaclient/contract.py](uaclient/contract.py).

### Timer jobs
UA client sets up a systemd timer to run jobs that need to be executed recurrently.
The timer itself ticks every 6 hours on average, and decides which jobs need
to be executed based on their _intervals_.

Jobs are executed by the timer script if:
- The script has not yet run successfully, or
- Their interval since last successful run is already exceeded.

There is a random delay applied to the timer, to desynchronize job execution time
on machines spun at the same time, avoiding multiple synchronized calls to the
same service.

Current jobs being checked and executed are:

| Job | Description | Interval |
| --- | ----------- | -------- |
| update_messaging | Update MOTD and APT messages | 6 hours |
| update_status | Update UA status | 12 hours |

- The `update_messaging` job makes sure that the MOTD and APT messages match the
available/enabled services on the system, showing information about available
packages or security updates. See [MOTD messages](#motd-messages).
- The `update_status` job makes sure the `ua status` command will have the latest
information even when executed by a non-root user, updating the
`/var/lib/ubuntu-advantage/status.json` file.

The timer intervals can be changed using the `ua config set` command.
```bash
# Make the update_status job run hourly
$ sudo ua config set update_status_timer=3600
```
Setting an interval to zero disables the job.
```bash
# Disable the update_status job
$ sudo ua config set update_status_timer=0
```

## Directory layout
The following describes the intent of UA client related directories:


| File/Directory | Intent |
| -------- | -------- |
| ./tools | Helpful scripts used to publish, release or test various aspects of UA client |
| ./features/ | Behave BDD integration tests for UA Client
| ./uaclient/ | collection of python modules which will be packaged into ubuntu-advantage-tools package to deliver the UA Client CLI |
| uaclient.entitlements | Service-specific \*Entitlement class definitions which perform enable, disable, status, and entitlement operations etc. All classes derive from base.py:UAEntitlement and many derive from repo.py:RepoEntitlement |
| ./uaclient/cli.py | The entry-point for the command-line client
| ./uaclient/clouds/ | Cloud-platform detection logic used in Ubuntu Pro to determine if a given should be auto-attached to a contract |
| uaclient.contract | Module for interacting with the Contract Server API |
| ./demo | Various stale developer scripts for setting up one-off demo environments. (Not needed often)
| ./apt-hook/ | the C++ apt-hook delivering MOTD and apt command notifications about UA support services |
| ./apt-conf.d/ | apt config files delivered to /etc/apt/apt-conf.d to automatically allow unattended upgrades of ESM security-related components. If apt proxy settings are configured, an additional apt config file will be placed here to configure the apt proxy. |
| /etc/ubuntu-advantage/uaclient.conf | Configuration file for the UA client.|
| /var/lib/ubuntu-advantage/private | `root` read-only directory containing Contract API responses, machine-tokens and service credentials |
| /var/log/ubuntu-advantage.log | `root` read-only log of ubuntu-advantage operations |


## Collecting logs
The `ua collect-logs` command creates a tarball with all relevant data for debugging possible problems with UA. It puts together:
- The UA Client configuration file (the default is `/etc/ubuntu-advantage/uaclient.conf`)
- The UA Client log files (the default is `/var/log/ubuntu-advantage*`)
- The files in `/etc/apt/sources.list.d/*` related to UA
- Output of `systemctl status` for the UA Client related services
- Status of the timer jobs, `canonical-livepatch`, and the systemd timers
- Output of `cloud-id`, `dmesg` and `journalctl`

Files with sensitive data are not included in the tarball. As of now, the command must be run as root.

Running the command creates a `ua_logs.tar.gz` file in the current directory.
The output file path/name can be changed using the `-o` option.

## Testing

All unit and lint tests are run using `tox`. We also use `tox-pip-version` to specify an older pip version as a workaround: we have some required dependencies that can't meet the strict compatibility checks of current pip versions.

First, install `tox` and `tox-pip-version` - you'll only have to do this once.

```shell
make testdeps
```

Then you can run the unit and lint tests:

```shell
tox
```

The client also includes built-in dep8 tests. These are run as follows:

```shell
autopkgtest -U --shell-fail . -- lxd ubuntu:xenial
```

### Integration Tests

ubuntu-advantage-client uses [behave](https://behave.readthedocs.io)
for its integration testing.

The integration test definitions are stored in the `features/`
directory and consist of two parts: `.feature` files that define the
tests we want to run, and `.py` files which implement the underlying
logic for those tests.

By default, integration tests will do the folowing on a given cloud platform:
 * Launch an instance running latest daily image of the target Ubuntu release
 * Add the Ubuntu advantage client daily build PPA: [ppa:ua-client/daily](https://code.launchpad.net/~ua-client/+archive/ubuntu/daily)
 * Install the appropriate ubuntu-advantage-tools and ubuntu-advantage-pro deb
 * Stop the instance and snapshot it creating an updated bootable image for
   test runs
 * Launch a fresh instance based on the boot-image created and exercise tests

The testing can be overridden to run using a local copy of the ubuntu-advantage-client source code instead of the daily PPA by providing the following environment variable to the behave test runner:
```UACLIENT_BEHAVE_BUILD_PR=1```

> Note that, by default, we cache the source even when `UACLIENT_BEHAVE_BUILD_PR=1`. This means that if you change the python code locally and want to run the behave tests against your new version, you need to either delete the cache (`rm /tmp/pr_source.tar.gz`) or also set `UACLIENT_BEHAVE_CACHE_SOURCE=0`.

To run the tests, you can use `tox`:

```shell
tox -e behave-20.04
```

or, if you just want to run a specific file, or a test within a file:

```shell
tox -e behave-20.04 features/unattached_commands.feature
tox -e behave-20.04 features/unattached_commands.feature:55
```

As can be seen, this will run behave tests only for release 20.04 (Focal Fossa). We are currently
supporting 4 distinct releases:

* 20.04 (Focal Fossa)
* 18.04 (Bionic Beaver)
* 16.04 (Xenial Xerus)
* 14.04 (Trusty Tahr)

Therefore, to change which release to run the behave tests against, just change the release version
on the behave command.

Furthermore, when developing/debugging a new scenario:

 1. Add a `@wip` tag decorator on the scenario
 2. To only run @wip scenarios run: `tox -e behave-20.04 -- -w`
 3. If you want to use a debugger:
    1. Add ipdb to integration-requirements.txt
    2. Add ipdb.set_trace() in the code block you wish to debug

(If you're getting started with behave, we recommend at least reading
through [the behave
tutorial](https://behave.readthedocs.io/en/latest/tutorial.html) to get
an idea of how it works, and how tests are written.)

#### Iterating Locally

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

#### Optimizing total run time of integration tests with snapshots
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

#### Integration testing on EC2
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

In order to run EC2 tests the following environment variables are required:
  - UACLIENT_BEHAVE_AWS_ACCESS_KEY_ID
  - UACLIENT_BEHAVE_AWS_SECRET_ACCESS_KEY


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

* To manually run EC2 integration tests using packages from `ppa:ua-client/daily` provide the following environment vars:

```sh
UACLIENT_BEHAVE_AWS_ACCESS_KEY_ID=<blah> UACLIENT_BEHAVE_AWS_SECRET_KEY=<blah2> tox -e behave-awspro-20.04
```

* To manually run EC2 integration tests with a specific AMI Id provide the
following environment variable to launch your specfic  AMI instead of building
a daily ubuntu-advantage-tools image.
```sh
UACLIENT_BEHAVE_REUSE_IMAGE=your-custom-ami tox -e behave-awspro-20.04
```

#### Integration testing on Azure
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

In order to run Azure tests the following environment variables are required:
  - UACLIENT_BEHAVE_AZ_CLIENT_ID
  - UACLIENT_BEHAVE_AZ_CLIENT_SECRET
  - UACLIENT_BEHAVE_AZ_SUBSCRIPTION_ID
  - UACLIENT_BEHAVE_AZ_TENANT_ID


To specifically run non-ubuntu pro tests using canonical cloud-images an
additional token obtained from https://ubuntu.com/advantage needs to be set:
  - UACLIENT_BEHAVE_CONTRACT_TOKEN=<your_token>

* To manually run Azure integration tests using packages from `ppa:ua-client/daily` provide the following environment vars:

```sh
UACLIENT_BEHAVE_AZ_CLIENT_ID=<blah> UACLIENT_BEHAVE_AZ_CLIENT_SECRET=<blah2> UACLIENT_BEHAVE_AZ_SUBSCRIPTION_ID=<blah3> UACLIENT_BEHAVE_AZ_TENANT_ID=<blah4> tox -e behave-azurepro-20.04
```

* To manually run Azure integration tests with a specific Image Id provide the
following environment variable to launch your specfic Image Id instead of building
a daily ubuntu-advantage-tools image.
```sh
UACLIENT_BEHAVE_REUSE_IMAGE=your-custom-image-id tox -e behave-awspro-20.04
```

### MOTD Messages

Since ubuntu-advantage-tools is responsible for enabling ESM services, we advertise them on different
applications thorough the system, such as MOTD and apt commands like upgrade.

To verify that the MOTD message is advertising the ESM packages, ensure that we have ESM source list
files in the system. If that is the case, please run the following commands to update the state of
MOTD and display the message:

```sh
# Make sure ubuntu-advantage-tools version >= 27.0
ua version
# Make apt aware of the ESM source files
sudo apt update
# Generates ubuntu-advantage-tools messages that should be delivered to MOTD
# This script is triggered by the systemd timer 4 times a day. To test it, we need
# to enforce that it was already executed.
sudo systemctl start ua-timer.service
# Force updating MOTD messages related to update-notifier
sudo rm /var/lib/ubuntu-advantage/jobs-status.json
sudo python3 /usr/lib/ubuntu-advantage/timer.py
# Update MOTD and display the message
run-parts /etc/update-motd.d/
```

## Building

Packages ubuntu-advantage-tools and ubuntu-advantage-pro are created from the
debian/control file in this repository. You can build the
packages the way you would normally build a Debian package:


```shell
dpkg-buildpackage -us -uc
```

**Note** It will build the packages with dependencies for the Ubuntu release on
which you are building, so it's best to build in a container or kvm for the
release you are targeting.

OR, if you want to build for a target release other than the release
you're on:

### using sbuild
[configure sbuild](https://wiki.ubuntu.com/SimpleSbuild) and
use that for the build:

Setup some chroots for sbuild with this script
```shell
bash ./tools/setup_sbuild.sh
```

```shell
debuild -S
sbuild --dist=<target> ../ubuntu-advantage-tools_*.dsc
# emulating different architectures in sbuild-launchpad-chroot
sbuild-launchpad-chroot create --architecture="riscv64" "--name=focal-riscv64" "--series=focal
```

> Note: Every so often, it is recommended to update your chroots.
> ```bash
> # to update a single chroot
> sudo sbuild-launchpad-chroot update -n ua-xenial-amd64
> # this script can be used to update all chroots
> sudo PATTERN=\* sh /usr/share/doc/sbuild/examples/sbuild-debian-developer-setup-update-all
> ```

### Setting up an lxc development container
```shell
lxc launch ubuntu-daily:trusty dev-t -c user.user-data="$(cat tools/ua-dev-cloud-config.yaml)"
lxc exec dev-t bash
```

### Setting up a kvm development environment with multipass
**Note:** There is a sample procedure documented in tools/multipass.md as well.
```shell
multipass launch daily:focal -n dev-f --cloud-init tools/ua-dev-cloud-config.yaml
multipass connect dev-f
```

## Code Formatting

The `ubuntu-advantage-client` code base is formatted using
[black](https://github.com/psf/black), and imports are sorted with
[isort](https://github.com/PyCQA/isort).  When making changes, you
should ensure that your code is blackened and isorted, or it will
be rejected by CI.
Formatting the whole codebase is as simple as running:

```shell
black uaclient/
isort uaclient/
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
which will build the client and place it in the [ua-client-daily PPA](https://code.launchpad.net/~ua-client/+archive/ubuntu/daily).

## Releasing ubuntu-advantage-tools
See [How to release a new version of UA](./contributing-docs/howtoguides/how_to_release_a_new_version_of_ua.md)
