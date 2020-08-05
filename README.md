# Ubuntu Advantage Client

[![Build Status](https://travis-ci.org/canonical/ubuntu-advantage-client.svg?branch=master)](https://travis-ci.org/github/canonical/ubuntu-advantage-client)

The Ubuntu Advantage client provides users with a simple mechanism to
view, enable, and disable offerings from Canonical on their system. The
following entitlements are supported:

- [Common Criteria EAL2 certification artifacts provisioning](https://ubuntu.com/cc-eal)
- [Canonical CIS Benchmark Audit Tool](https://ubuntu.com/cis-audit)
- [Ubuntu Extended Security Maintenance](https://ubuntu.com/esm)
- [FIPS 140-2 Certified Modules](https://ubuntu.com/fips)
- [FIPS 140-2 Non-Certified Module Updates](https://ubuntu.com/fips)
- [Livepatch Service](https://www.ubuntu.com/livepatch)

## Obtaining the Client

The client comes pre-installed on all Ubuntu systems in the debian packages
`ubuntu-advantage-tools` package. Ubuntu Pro images on AWS and Azure Ubuntu Pro
images will also contain `ubuntu-advantage-pro` which automates machine attach
on custom AWS and Azure images.

Users can manually run the `ua` command to learn more or view the manpage.

## Terminology
 The following vocabulary is used to describe different aspects of the work
Ubuntu Advantage Client performs:

| Term | Meaning |
| -------- | -------- |
| UA Client | The python command line client represented in this ubuntu-advantage-client repository. It is installed on each Ubuntu machine and is the entry-point to enable any Ubuntu Advantage commercial service on an Ubuntu machine. |
| Contract Server | The backend service exposing a REST API to which UA Client authenticates in order to obtain contract and commercial service information and manage which support services are active on a machine.|
| Entitlement/Service | An Ubuntu Advantage commercial support service such as FIPS, ESM, Livepatch, CIS-Audit to which a contract may be entitled |
| Affordance | Service-specific list of applicable architectures and Ubuntu series on which a service can run |
| Directives | Service-specific configuration values which are applied to a service when enabling that service |
| Obligations | Service-specific policies that must be instrumented for support of a service. Example: `enableByDefault: true` means that any attached machine **MUST** enable a service on attach |


## Architecture
Ubuntu Advantage client, hereafter "UA client", is python3-based command line
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
validate such operations. The contract server API is described by the
[ua-contracts openapi spec](https://github.com/CanonicalLtd/ua-contracts/blob/develop/docs/contracts.yaml).

### Attaching a machine
Each Ubuntu SSO account holder has access to one or more contracts. To attach
a machine to an Ubuntu Advantage contract:

* An Ubuntu SSO account holder must obtain a contract token from
https://ubuntu.com/advantage.
* Run `sudo ua attach <contractToken>` on the machine
  - Ubuntu Pro images for AWS and Azure perform an auto-attach without tokens
* UA Client reads config from /etc/ubuntu-advantage/uaclient.conf to obtain
  the contract_url (default: https://contracts.canonical.com)
* UA Client POSTs to the Contract Server API @
  <contract_url>/api/v1/context/machines/token providing the \<contractToken\>
* The Contract Server responds with a JSON blob containing an unique machine
  token, service credentials, affordances, directives and obligations to allow
  enabling and disabling Ubuntu Advantage services
* UA client writes the machine token API response to the root-readonly
  /var/lib/ubuntu-advantage/machine-token.json
* UA client auto-enables any services defined with
  `obligations:{enableByDefault: true}`

### Enabling a service
Each service controlled by UA client will have a python module in
uaclient/entitlements/\*.py which handles setup and teardown of services when
enabled or disabled.

If a contract entitles a machine to a service, `root` user can enable the
service with `ua enable <service>`.  If a service can be disabled
`ua disabled <service>` will be permitted.

The goal of the UA client is to remain simple and flexible and let the
contracts backend drive dynamic changes in contract offerings and constraints.
In pursuit of that goal, the UA client obtains most of it's service constraints
from a machine token that it obtains from the Contract Server API.

The UA Client is simple in that it relies on the machine token on the attached
machine to describe whether a service is applicable for an environment and what
configuration is required to properly enable that service.

Any interactions with the Contract server API are defined as UAContractClient
class methods in [uaclient/contract.py](uaclient/contract.py).

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
| ./apt-conf.d/ | apt config files delivered to /etc/apt/apt-conf.d to automatically allow unattended upgrades of ESM  security-related components |
| /etc/ubuntu-advantage/uaclient.conf | Configuration file for the UA client.|
| /var/lib/ubuntu-advantage/private | `root` read-only directory containing Contract API responses, machine-tokens and service credentials |
| /var/log/ubuntu-advantage.log | `root` read-only log of ubuntu-advantage operations |


## Testing

All unit and lint tests are run using tox:

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
 * Add the Ubuntu advantage client daily build PPA: [ppa:canonical-server/ua-client-daily](https://code.launchpad.net/~canonical-server/+archive/ubuntu/ua-client-daily)
 * Install the appropriate ubuntu-advantage-tools and ubuntu-advantage-pro deb
 * Stop the instance and snapshot it creating an updated bootable image for
   test runs
 * Launch a fresh instance based on the boot-image created and exercise tests

The testing can be overridden to run using a local copy of the ubuntu-advantage-client source code instead of the daily PPA by providing the following environment variable to the behave test runner.
```UACLIENT_BEHAVE_BUILD_PR=1```

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
 4. If you want to use a debugger:
    a. Add ipdb to integration-requirements.txt
    b. Add ipdb.set_trace() in the code block you wish to debug

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

#### Integration testing on EC2 PRO images

Any ec2 pro image BDD tests are decorated with:
    @uses.config.machine_type.pro.aws

Providing the environment variable `UACLIENT_BEHAVE_MACHINE_TYPE="pro.aws"`
will limit test cases executed to AWS Ubuntu PRO only.

By default, the public AMIs for Ubuntu Pro testing used for each Ubuntu
release are defined in features/aws-ids.yaml. These ami-ids are determined by
running ./tools

Integration tests will read features/aws-ids.yaml to determine which default
AMI id to use for each supported Ubuntu release.

To update `features/aws-ids.yaml`, run `./tools/refresh-aws-pro-ids` and put up
a pull request against this repo to updated that content from the ua-contracts
marketplace definitions.

* To manually run EC2 integration tests using packages from `ppa:canonical-server/ua-client-daily` provide the following environment vars:

```sh
UACLIENT_BEHAVE_MACHINE_TYPE="pro.aws" UACLIENT_BEHAVE_AWS_ACCESS_KEY_ID=<blah> UACLIENT_BEHAVE_AWS_SECRET_KEY=<blah2> tox -e behave-18.04
```

* To manually run EC2 integration tests with a specific AMI Id provide the
following environment variable to launch your specfic  AMI instead of building
a daily ubuntu-advantage-tools image.
```sh
UACLIENT_BEHAVE_REUSE_IMAGE=ami-your-custom-ami tox -e behave-18.04
```

## Building

Creating ubuntu-advantage-tools and ubuntu-advantage-pro is created from the
debian/control file in this repository. You can build the
package the way you would normally build a Debian package:


```shell
dpkg-buildpackage -us -uc
```

**Note** It will build the package with dependencies for the Ubuntu release on
which you are building, so it's best to build in a container of kvm for the
release you are targeting.

OR, if you want to build for a target release other than the release
you're on:

### using sbuild
[configure sbuild](https://wiki.ubuntu.com/SimpleSbuild) and
use that for the build:


```shell
debuild -S
sbuild --dist=<target> ../ubuntu-advantage-tools_*.dsc
```

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

## Releasing ubuntu-adantage-tools
see [RELEASES.md](RELEASES.md)
