.. _getting_started_devel:

Get started developing for Ubuntu Pro Client
********************************************

This tutorial will walk you through getting your development environment set
up from scratch for contributing to Ubuntu Pro Client.

We generally support the latest interim release and the latest LTS of Ubuntu
as development hosts for Ubuntu Pro Client.

.. note::
   This tutorial was last tested on Ubuntu 23.10 (Mantic Minotaur).

From nothing to unit tests
==========================

In your terminal, install necessary host tooling:

.. code-block:: bash

   sudo apt install git tox pre-commit intltool libapt-pkg-dev sbuild-launchpad-chroot

.. note::
   Python comes installed by default on Ubuntu. Do not install Python via any
   non-Ubuntu means. That includes ``conda``, ``pyenv``, ``asdf``,
   ``ppa:deadsnakes/ppa``, download from ``python.org``, etc.

Get the code:

.. code-block:: bash

   git clone https://github.com/canonical/ubuntu-pro-client.git
   cd ubuntu-pro-client

Initialise ``pre-commit``:

.. code-block:: bash

   pre-commit install

``pre-commit`` will run ``black``, ``isort``, and ``shellcheck`` on any files
you edit in a commit. If it makes any changes or finds problems, it will abort
the commit. You can then ``git add`` the changes it made, or fix the issues,
and then ``git commit`` again.

Run the unit tests and other checks:

.. code-block:: bash

   tox

``tox`` manages separate virtual environments for each of the different jobs
we run. For each job, it will install all of the dependencies into the virtual
environment, and then run the job. This ensures that the dependencies for each
job don't interfere with each other.

.. note::
   You can run individual jobs (or "environments" in ``tox`` terminology) with
   the ``-e`` flag.

   For example:
   
   - ``tox -e test`` will run the unit tests
   - ``tox -e flake8`` will run the Python linter
   - ``tox -e mypy`` will run the type checker
   - ``tox -e shellcheck`` will run the bash script linter 
   - ``tox -e behave`` will run the integration tests (discussed more later)

Explore ``tox.ini`` to see what tox environments are available and how they're
configured.

Getting to basic behave tests
=============================

We use `behave <https://behave.readthedocs.io/en/stable/>`_ as a framework for
writing integration, acceptance, and regression tests. Behave tests are in the
``features/`` folder and generally follow the pattern of:

1. Launch a VM or container on a platform (LXD, AWS, Azure, GCP, etc.)
2. Install the version of Ubuntu Pro Client we want to test
3. Run commands on the system to exercise some feature of Pro Client
4. Assert that the expected results occurred

The most common behave tests use LXD as the platform. So we need the host to
support launching LXD containers and VMs.

Setting up LXD
==============

Install LXD:

.. code-block:: bash

   sudo snap install lxd

Add yourself to the ``lxd`` group and use ``newgrp`` to apply the change
without logging out and back in.

.. code-block:: bash

   sudo usermod -a -G lxd $USER
   newgrp lxd

Initialise ``lxd`` -- use the defaults.

.. code-block:: bash

   lxd init

Ubuntu Pro Client is unique in that it supports very old releases of Ubuntu,
including 16.04 LTS (Xenial Xerus). We test this support by using Xenial LXD
containers. For hosts running newer releases of Ubuntu to run Xenial
containers, we need to configure systemd to use an older cgroup version for
compatibility. This is configured by editing the Linux kernel boot parameters.

We need the boot parameters ``systemd.unified_cgroup_hierarchy=0`` and
``systemd.legacy_systemd_cgroup_controller``.

.. note::
   Unfortunately, this means your host will miss out on the benefits and safety
   features of cgroup v2, but it is necessary for developing and supporting
   Ubuntu Pro Client for Xenial.

Use `this how-to guide <https://wiki.ubuntu.com/Kernel/KernelBootParameters>`_
to edit your Linux kernel boot parameter. First make the change temporarily,
and ensure your system still boots and works. Then make the change permanently.

Now, with the boot parameter in place, test that a Xenial container can start
and reach the network.

.. code-block:: bash

   lxc launch ubuntu-daily:xenial testx
   lxc shell testx
   # now you should be inside the container
   ping -c 3 ubuntu.com
   # the ping command should succeed
   exit
   # now you should be back on your host
   lxc delete --force testx

.. note::
   Docker can interfere with LXD container networking. If you need Docker
   installed alongside LXD, follow the guidance in
   `the LXD documentation <https://documentation.ubuntu.com/lxd/en/latest/howto/network_bridge_firewalld/#prevent-connectivity-issues-with-lxd-and-docker>`_
   to ensure that Docker doesn't break LXD networking.

Building Ubuntu Pro Client for testing
--------------------------------------

To install a local version of Ubuntu Pro Client in a LXD container, we need to
build a deb package. We have a script that will set up the environment needed
to build debs for any target Ubuntu release.

At time of writing, Ubuntu Pro Client supports the Ubuntu releases in this
example command. You may need to adjust the command in the future as Ubuntu
releases come and go.

This command also assumes you are on an AMD64 system. You will have to adjust
the command accordingly if you are not.

.. code-block:: bash

   env RELEASES="xenial bionic focal jammy mantic noble" ARCHS="amd64" bash tools/setup_sbuild.sh

This command will take some time. It sets up schroots for each release with the
dependencies of Ubuntu Pro Client pre-installed. This will make building the
deb packages for each release go faster. As time goes by, Ubuntu releases get
updates which need to be installed for each build; you can re-run the
``setup_sbuild.sh`` script and it will update the schroots to keep your Pro
Client builds fast.

You will also need to run the following to ensure your user can use the schroots.

.. code-block:: bash

   sudo sbuild-adduser $USER
   newgrp sbuild

After that is complete, try out a Xenial build.

.. code-block:: bash

   ./tools/build.sh xenial

Configuring pycloudlib
----------------------

We use `pycloudlib <https://github.com/canonical/pycloudlib>`_ to manage
instances on clouds for our behave tests, and local LXD containers are treated
as a "cloud" by pycloudlib.

To get started, we just need a basic configuration of pycloudlib. Copy the
contents of ``pycloudlib.toml.template`` from the source repository and save
it to ``~/.config/pycloudlib.toml`` on your machine.

.. code-block:: bash

   wget https://raw.githubusercontent.com/canonical/pycloudlib/main/pycloudlib.toml.template -O ~/.config/pycloudlib.toml

Run a simple behave test
------------------------

.. code-block:: bash

   tox -e behave -- features/config.feature -D releases=xenial -D machine_types=lxd-container

All of the arguments after the ``--`` are passed to behave. In this case, we're
telling behave to only run the ``config.feature`` test, and to filter the tests
in that file to only those for Xenial LXD containers. Note that the ``-D``
options are specific to our behave tests and are not behave options.

Configuring a contract token
----------------------------

Now that you have ``behave`` working, ask a member of the Ubuntu Pro Client
team for the testing contract tokens. There are three of them. You will need to
set them as values of environment variables in your shell.

.. code-block:: bash

   export UACLIENT_BEHAVE_CONTRACT_TOKEN=contract_token
   export UACLIENT_BEHAVE_CONTRACT_TOKEN_STAGING=contract_token_staging
   export UACLIENT_BEHAVE_CONTRACT_TOKEN_STAGING_EXPIRED=contract_token_staging_expired

Now you can run tests that use ``pro`` to attach to an Ubuntu Pro contract.

.. code-block:: bash

   tox -e behave -- -n "snapd installed as a snap if necessary"

Notice that we're using the ``-n`` option to behave to filter the tests to only
the one that matches the given string. This particular test happens to also be
a test that uses a LXD VM, so it is a good test to run to ensure that your LXD
VMs are working.

Interacting with local changes
==============================

With all of the above in place, you can now make changes to the code and run a
local version of Ubuntu Pro Client in a LXD container or Multipass VM to try
out your changes.

Edit ``uaclient/version.py`` and modify the ``get_version()`` function to
return a fake version string. For example, change the first line of the
function to ``return "42:42"``.

Try it out in a container
-------------------------

Now use our helper script to build a deb with your changes, launch a LXD
container, install your deb, and drop you into a shell on the container.

.. code-block:: bash

   ./tools/test-in-lxd.sh xenial

In the container, you can now run ``pro version`` and see your changes in
action.

When you're done with the container, ``exit`` and remember to delete the
container. The name of the container contains a unique hash of the version of
``pro`` you built; you can find it as the hostname of the container in the
prompt of your shell, or by running ``lxc list`` on your host machine.

Try it out in a VM
------------------

While we use LXD VMs for behave tests, it is difficult to set up Xenial and
Bionic VMs manually for interactive testing. Instead, we use
`Multipass <https://multipass.run/>`_ to launch VMs for interactive testing.

Install Multipass:

.. code-block:: bash

   sudo snap install multipass

Now use our helper script to build a deb with your changes, launch a Multipass
VM, install your deb, and drop you into a shell on the VM.

.. code-block:: bash

   ./tools/test-in-multipass.sh xenial

In the VM, you can now run ``pro version`` and see your changes in action.

When you're done with the VM, ``exit`` and remember to delete the VM. The
name of the VM contains a unique hash of the version of ``pro`` you built; you
can find it as the hostname of the VM in the prompt of your shell, or by
running ``multipass list`` on your host machine.

