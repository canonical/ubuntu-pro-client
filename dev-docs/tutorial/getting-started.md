# Get started developing for Ubuntu Pro Client

This tutorial will walk you through getting your development environment set up
from scratch for contributing to Ubuntu Pro Client.

We generally support the latest interim release and the latest LTS of Ubuntu as
development hosts for Ubuntu Pro Client.

> **Note**
> This tutorial was last tested on Ubuntu 23.10 Mantic Minotaur (`mantic`).

## From nothing to unit tests

### Using Workshop (recommended)

See [Set up Workshop](../how-to/setup-workshop.md) for step-by-step instructions.

### Using the tooling directly (alternative)

If you prefer to manage the toolchain yourself, install the necessary host
tooling:

```bash
sudo apt install git tox pre-commit intltool libapt-pkg-dev
```

> **Note**
> Python comes installed by default on Ubuntu. Do not install Python via any
non-Ubuntu means. That includes `conda`, `pyenv`, `asdf`, `ppa:deadsnakes/ppa`,
download from `python.org`, etc.

Get the code:

```bash
git clone https://github.com/canonical/ubuntu-pro-client.git
cd ubuntu-pro-client
```

Initialise `pre-commit`:

```bash
pre-commit install
```

`pre-commit` will run `black`, `isort`, and `shellcheck` on any files you edit
in a commit. If it makes any changes or finds problems, it will abort the
commit. You can then `git add` the changes it made, or fix the issues, and then
`git commit` again.

Run the unit tests and other checks:

```bash
tox
```

`tox` manages separate virtual environments for each of the different jobs we
run. For each job, it will install all of the dependencies into the virtual
environment, and then run the job. This ensures that the dependencies for each
job don't interfere with each other.

> **Note**
> You can run individual jobs (or "environments" in `tox` terminology) with the
> `-e` flag.
>
> For example:
> - `tox -e test` will run the unit tests.
> - `tox -e flake8` will run the Python linter.
> - `tox -e mypy` will run the type checker.
> - `tox -e shellcheck` will run the bash script linter.
> - `tox -e behave` will run the integration tests (discussed more later).
>
> Explore `tox.ini` to see what tox environments are available and how they're configured.

## Getting to basic behave tests

We use [`behave`](https://behave.readthedocs.io/en/stable/) as a framework for
writing integration, acceptance, and regression tests. Behave tests are in the
`features/` folder and generally follow the pattern of:

1. Launch a VM or container on a platform (LXD, AWS, Azure, GCP, etc.)
2. Install the version of Ubuntu Pro Client we want to test
3. Run commands on the system to exercise some feature of Pro Client
4. Assert that the expected results occurred

The most common behave tests use LXD as the platform. So we need the host to
support launching LXD containers and VMs.

## Setting up LXD

Install `lxd`:

```bash
sudo snap install lxd
```

> **Note**
> We develop and test against LXD 6.x (the version available on recent Ubuntu
> LTS releases such as Noble). Older LXD versions are not supported for running
> the integration tests.

Add yourself to the `lxd` group and use `newgrp` to apply the change without
logging out and back in:

```bash
sudo usermod -a -G lxd $USER
newgrp lxd
```

Initialise `lxd` -- use the defaults:

```bash
lxd init
```

Test that a container for the oldest release that `main` supports can start
and reach the network:

```bash
lxc launch ubuntu-daily:bionic test-bionic
lxc shell test-bionic
# now you should be inside the container
ping -c 3 ubuntu.com
# the ping command should succeed
exit
# now you should be back on your host
lxc delete --force test-bionic
```

> **Note**
> Docker can interfere with LXD container networking. If you need Docker
> installed alongside LXD, follow the guidance in
> [the LXD documentation](https://documentation.ubuntu.com/lxd/en/latest/howto/network_bridge_firewalld/#prevent-connectivity-issues-with-lxd-and-docker)
> to ensure that Docker doesn't break LXD networking.

## Building Ubuntu Pro Client for testing

To install a local version of Ubuntu Pro Client in a LXD container, we need to
build a deb package. We build with `sbuild`, which creates a clean build root
for each target Ubuntu release with `mmdebstrap` and no root access.

This requires Ubuntu 24.04 or later on the host. On 24.04, install `sbuild`
from `noble-backports`, because the release's own version can't create build
roots this way:

```bash
sudo apt install -t noble-backports sbuild mmdebstrap uidmap
```

On Ubuntu 25.10 and later, install the same packages without `-t`.

Build for any supported release with:

```bash
./tools/build.sh noble
```

The first build for a release downloads and caches a build root, so it takes
longer than later builds. CI builds packages with the same command, so a
local build matches what CI produces. `tools/sbuild-config.pl` holds the `sbuild`
configuration that the build uses.

### Configuring pycloudlib

We use [`pycloudlib`](https://github.com/canonical/pycloudlib) to manage
instances on clouds for our behave tests, and local LXD containers are treated
as a "cloud" by pycloudlib.

To get started, we just need a basic configuration of pycloudlib. Copy the
contents of `pycloudlib.toml.template` from the source repository and save it
to `~/.config/pycloudlib.toml` on your machine:

```bash
wget https://raw.githubusercontent.com/canonical/pycloudlib/main/pycloudlib.toml.template -O ~/.config/pycloudlib.toml
```

### Run a simple behave test

```bash
tox -e behave -- features/config.feature -D releases=bionic -D machine_types=lxd-container
```

All of the arguments after the `--` are passed to behave. In this case, we're
telling behave to only run the `config.feature` test, and to filter the tests
in that file to only those for Bionic LXD containers. Note that the `-D`
options are specific to our behave tests and are not behave options.

### Configuring a contract token

Now that you have `behave` working, ask a member of the Ubuntu Pro Client team
for the testing contract tokens. There are three tokens. You will need to set
them as values of environment variables in your shell.

```bash
export UACLIENT_BEHAVE_CONTRACT_TOKEN=contract_token
export UACLIENT_BEHAVE_CONTRACT_TOKEN_STAGING=contract_token_staging
export UACLIENT_BEHAVE_CONTRACT_TOKEN_STAGING_EXPIRED=contract_token_staging_expired
```

Now you can run tests that use `pro` to attach to an Ubuntu Pro contract:

```bash
tox -e behave -- -n "snapd installed as a snap if necessary"
```

Notice that we're using the `-n` option to behave to filter the tests to only
the one that matches the given string. This particular test happens to also be
a test that uses a LXD VM, so it is a good test to run to ensure that your LXD
VMs are working.

## Interacting with local changes

With all of the above in place, you can now make changes to the code and run a
local version of Ubuntu Pro Client in a LXD container or Multipass VM to try
out your changes.

Edit `uaclient/version.py` and modify the `get_version()` function to return a
fake version string. For example, change the first line of the function to
`return "42:42"`.

### Try it out in a container

Now use our helper script to build a deb with your changes, launch a LXD
container, install your deb, and drop you into a shell on the container:

```bash
./tools/test-in-lxd.sh bionic
```

In the container, you can now run `pro version` and see your changes in action.

When you're done with the container, `exit` and remember to delete the
container. The name of the container contains a unique hash of the version of
`pro` you built; you can find it as the hostname of the container in the prompt
of your shell, or by running `lxc list` on your host machine.

### Try it out in a VM

While we use LXD VMs for behave tests, it is difficult to set up Bionic VMs
manually for interactive testing. Instead, we use
[Multipass](https://multipass.run/) to launch VMs for interactive testing.

Install Multipass.

```bash
sudo snap install multipass
```

Now use our helper script to build a deb with your changes, launch a Multipass
VM, install your deb, and drop you into a shell on the VM.

```bash
./tools/test-in-multipass.sh bionic
```

In the VM, you can now run `pro version` and see your changes in action.

When you're done with the VM, `exit` and remember to delete the VM. The name of
the VM contains a unique hash of the version of `pro` you built; you can find
it as the hostname of the VM in the prompt of your shell, or by running
`multipass list` on your host machine.
