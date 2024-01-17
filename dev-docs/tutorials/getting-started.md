# Get started developing for Ubuntu Pro Client

This tutorial will walk you through getting your development environment set up from scratch for contributing to Ubuntu Pro Client.

We generally support the latest interim release and the latest LTS of Ubuntu as development hosts for Ubuntu Pro Client.

> **Note**
> This tutorial was last tested on Ubuntu 23.10 Mantic Minotaur (mantic).

# From nothing to unit tests
Open a terminal.

Install necessary host tooling.
```bash
sudo apt install git tox pre-commit intltool libapt-pkg-dev sbuild-launchpad-chroot
```
> **Note**
> Python comes installed by default on Ubuntu.
> Do not install python via any non-Ubuntu means. That includes conda, pyenv, asdf, ppa:deadsnakes/ppa, download from python.org, etc.

Get the code.
```bash
git clone https://github.com/canonical/ubuntu-pro-client.git
cd ubuntu-pro-client
```

Initialize `pre-commit`.
```bash
pre-commit install
```

Run the unit tests and other checks.
```bash
tox
```

> **Note**
> You can run individual jobs (or "environments" in tox terminology) with the `-e` flag.
>
> For example, `tox -e test` will only run the unit tests.
>
> Explore `tox.ini` to see what tox environments are available and how they're configured.

# Getting to basic behave tests
We use [`behave`](https://behave.readthedocs.io/en/stable/) as a framework for writing integration/acceptance/regression tests. behave tests are in the `features/` folder and generally follow the pattern of:
1. Launch a VM or container on a platform
2. Install the version of Ubuntu Pro Client we want to test
3. Run commands on the system to exercise some feature of Pro Client
4. Assert that the expected results occurred

The most common behave tests use lxd as the platform. So we need the host to support launching lxd containers and VMs.

## Setting up LXD
Install lxd.
```bash
sudo snap install lxd
```
Add yourself to the `lxd` group and use `newgrp` to apply the change without logging out and back in.
```bash
sudo usermod -a -G lxd $USER
newgrp lxd
```
Initialize lxd - use the defaults.
```bash
lxd init
```

Ubuntu Pro Client is unique in that it supports very old releases of Ubuntu, including 16.04 Xenial Xerus (xenial). We test this support by using xenial lxd containers. In order for hosts running newer releases of Ubuntu to run xenial containers, we need to configure systemd to use an older cgroup hierarchy for compatibility. This is configured by editing the linux kernel boot parameters.

We need the boot parameter `systemd.unified_cgroup_hierarchy=0`.

Use the following how-to-guide to edit your linux kernel boot parameter. First make the change temporarily, and ensure your system still boots and works. Then make the change permanently. The how-to-guide is here: https://wiki.ubuntu.com/Kernel/KernelBootParameters.

Now, with the boot parameter in place, test that a xenial container can start and reach the network.
```bash
lxc launch ubuntu-daily:xenial testx
lxc shell testx
# now you should be inside the container
ping -c 3 ubuntu.com
# the ping command should succeed
exit
# now you should be back on your host
lxc delete --force testx
```

> **Note**
> Docker can interfere with lxd container networking. If you need docker installed alongside lxd, follow the guidance in the lxd documentation to ensure that docker doesn't break lxd networking: https://documentation.ubuntu.com/lxd/en/latest/howto/network_bridge_firewalld/#prevent-connectivity-issues-with-lxd-and-docker

## Building Ubuntu Pro Client for testing

In order to install a local version of Ubuntu Pro Client in a lxd container, we need to build a `deb` package. We have a script that will set up the environment necessary to build debs for any target Ubuntu release.

At time of writing, Ubuntu Pro Client supports the Ubuntu releases in this example command. You may need to adjust the command in the future as Ubuntu releases come and go.

This command also assumes you are on an `amd64` system. You will have to adjust the command accordingly if you are not.

```bash
env RELEASES="xenial bionic focal jammy mantic noble" ARCHS="amd64" bash tools/setup_sbuild.sh
```

This command will take some time. It sets up schroots for each release with the dependencies of Ubuntu Pro Client pre-installed. This will make building the deb packages for each release go faster. As time goes by, Ubuntu releases get updates which need to be installed for each build; you can re-run the setup_sbuild.sh script and it will update the schroots to keep your pro-client builds fast.

You will also need to run the following to ensure your user can use the schroots.
```bash
sudo sbuild-adduser $USER
newgrp sbuild
```

After that is complete, try out a xenial build.
```bash
./tools/build.sh xenial
```

## Configuring pycloudlib

We use [`pycloudlib`](https://github.com/canonical/pycloudlib) to manage instances on clouds for our behave tests, and local lxd containers are treated as a "cloud" by pycloudlib.

To get started, we just need a basic configuration of pycloudlib. Copy the contents of the pycloudlib.toml.template from the source repository and save it to `~/.config/pycloudlib.toml` on your machine.
```bash
wget https://raw.githubusercontent.com/canonical/pycloudlib/main/pycloudlib.toml.template -O ~/.config/pycloudlib.toml
```

## Run a behave test

```bash
tox -e behave -- features/config.feature -D releases=xenial -D machine_types=lxd-container
```

All of the arguments after the `--` are passed to behave. In this case, we're telling behave to only run the `config.feature` test, and to filter the tests in that file to only those for xenial lxd containers. Note that the `-D` options are specific to our behave tests and are not behave options.

# Interacting with local changes in a container
With all of the above in place, you can now make changes to the code and run a local version of Ubuntu Pro Client in a lxd container to try out your changes.

Edit `uaclient/version.py` and modify the `get_version()` function to return a fake version string. For example, change the first line of the function to `return "42:42"`.

Now use our helper script to build a deb with your changes, launch a lxd container, install your deb, and drop you into a shell on the container.
```bash
./tools/test-in-lxd.sh xenial
```
In the container, you can now run `pro version` and see your changes in action.

When you're done with the container, `exit` and remember to delete the container. The name of the container contains a unique hash of the version of `pro` you built; you can find it as the hostname of the container in the prompt of your shell, or by running `lxc list` on your host machine.
