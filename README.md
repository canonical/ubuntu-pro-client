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

The client comes pre-installed on all Ubuntu systems in the debian packages
`ubuntu-advantage-tools` and `ubuntu-advantage-pro`. Users can run the `ua` command to learn more or view
the manpage.

## Terminology
 The following vocabulary is used to describe different aspects of the work Ubuntu Advantage Client performs:

| Term | Meaning |
| -------- | -------- |
| UA Client | The python command line client represented in this ubuntu-advantage-client repository. It is installed on each Ubuntu machine and is the entry-point to enable any Ubuntu Advantage commercial service on an Ubuntu machine. |
| Contract Server | The backend service exposing a REST API to which UA Client authenticates in order to obtain contract and commercial service information and manage which support servics are active on a machine.|
| Entitlement/Service | An Ubuntu Advantage commercial support service such as FIPS, ESM, Livepatch, CIS-Audit to which a Contract may be entitled |
| Affordance | Service-specific list of applicable architectures and Ubuntu series on which a service can run |
| Directives | Service-specific configuration values which are applied to a service when enabling that service |
| Obligations | Service-specific policies that must be instrumented for support of a service. Example: `enableByDefault: true` means that any attached machine **MUST** enable a service on attach |


## Architecture
Ubuntu Advantage client, hereafter "UA client", is python3-based command line utility. It provides a CLI to attach, detach, enable,
disable and check status of support related services.

The package `ubuntu-advantage-tools` also provides a C++ APT hook which helps advertise ESM service and available packages in MOTD and during various apt commands.

The `ubuntu-advantage-pro` package delivers auto-attach auto-enable functionality via init scripts and systemd services for various cloud platforms.

By default, Ubuntu machines are deployed in an unattached state. A machine can get manually or automatically attached to a specific contract by interacting with the Contract Server REST API to enable a machine. Any change in state of services or machinbe attach results in additional interactions with the Contract Server API to validate such operations. The contract server API is described by the [ua-contracts openapi spec](https://github.com/CanonicalLtd/ua-contracts/blob/develop/docs/contracts.yaml).

### Attaching a machine
Each Ubuntu SSO account holder has access to one one or more contracts. To attach a machine to an Ubuntu Advantage contract:

* An Ubuntu SSO account holder must obtain a contract token from https://ubuntu.com/advantage.
* Run `ua attach <contractToken>` on the machine or provide comparable
* UA Client reads config from /etc/ubuntu-advantage/uaclient.conf nad  a request containing the `<contractToken>` to the Contract Server API @ https://<contract_url>/api/v1/context/machines/token and obtains an unique machine-token JSON response containing credentials, affordances, directives and obligations to allow enabling and disabling any Ubuntu Advantage service
* UA Client POSTs a request containing the `<contractToken>` to the Contract Server API @ https://contracts.canonical.com/api/v1/context/machines/tokento to obtain an unique machine-token JSON response which contains credentials, affordances, directives and obligations to allow enabling and disabling any Ubuntu Advantage service
* UA client auto-enables any services described with `obligations:{enableByDefault: true}`
POST `<contractToken>` to contracts server API @ https://contracts.canonical.com/api/v1/context/machines/token
* UA client writes the API response to the root-readonly /var/lib/ubuntu-advantage/machine-token.json

### Enabling a service
Each service controlled by UA client will have a python module in uaclient/entitlements/\*.py which handles setup and teardown of services when enabled or disabled.

If a contract entitles a machine to a service, `root` user can enable the service with `ua enable <service>`.  If a service can be disabled `ua disabled <service>` will be permitted.

The goal of the UA client is to remain simple and flexible and let the
contracts backend drive dynamic changes in contract offerings and contraints.
In pursuit of that goal, the UA client obtains most of it's service contraints
from a machine token that it ob

The UA Client is simple in that it relies on the machine token on the attached
machine to describe whether a service is applicable for an envronment and what
configuration is required to properly enable that service.

Any interactions with the Contract server API are defined as UAContractClient class methods in uaclient/contract.py.

## Directory layout
The following describes the intent of UA client related directories:


| File/Directory | Intent |
| -------- | -------- |
| ./tools | Helpful scripts used to publish, release or test various aspects of  UA client |
| .features/ | Behave BDD integration tests for UA Client
| uaclient/ | collection of python modules which will be packaged into ubuntu-advantage-tools package to deliver the UA Client CLI |
| uaclient.entitlements | Service-specific \*Entitlement class definitions which perform enable, disable, status, and entitlement operations etc. All classes derive from base.py:UAEntitlement and many derive from repo.py:RepoEntitlement |
| uaclient.cli | The entry-point for the command-line client
| uaclient.clouds | Cloud-platform detection logic used in Ubuntu Pro to determine if a given should be auto-attached to a contract |
| uaclient.contract | Module for interacting with the Contract Server API |
| ./demo | Various stale developer scripts for setting up one-off demo environemnts. (Not needed often)
| /etc/ubuntu-advantage/uaclient.conf | Configuration file for the UA client.|
| apt-hook | the C++ apt-hook delivering MOTD and apt command notifications about UA support services |
| apt-conf.d | apt config files delivered to /etc/apt/apt-conf.d to automatically allow unattended upgrades of ESM  security-related components |
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

To run the tests, you can use `tox`:

```shell
tox -e behave
```

or, if you just want to run a specific file, or a test within a file:

```shell
tox -e behave features/unattached_commands.feature
tox -e behave features/unattached_commands.feature:55
```

When developing/debugging a new scenario:

 1. Add a `@wip` tag decorator on the scenario
 2. To only run @wip scenarios run: `tox -e behave -- -w`
 3. If you want to use a debugger: Use ipdb.set_trace() in the code you
    wish to debug

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

## Building

The packaging for the UA client packages (ubuntu-advantage-tools/ubuntu-advantage-pro) is
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

## Releasing ubuntu-adantage-tools
see [RELEASES.md](RELEASES.md)
