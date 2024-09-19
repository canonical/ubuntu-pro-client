
Exploring your system's security with Pro
*****************************************

Whether you're running the latest Ubuntu LTS release, or a release at the end
of its standard support period, you are probably curious about the security
services that Ubuntu Pro provides.

In this tutorial, we will set up a virtual machine (VM) and use it to explore
some of the security-related services and commands available to all users, and
see how they can be used to keep your system safer and more secure.

.. Why we use Multipass + command to install it
.. include:: ./common/install-multipass.txt

Use Multipass to create a VM
============================

We're going to create our VM using the Ubuntu 18.04 LTS (Bionic Beaver). It is
the most recent LTS to reach the end of its standard support period (as of the
time of writing), so it has updates available through the Ubuntu Pro Expanded
Security Maintenance (ESM) services. 

Let's start by creating our VM by running the following command:

.. code-block:: bash

   $ multipass launch bionic --name test-vm

This command will create (``launch``) a Bionic VM that we will label with the
name "``test-vm``".

It will probably take a few minutes to fetch the Bionic image (depending on
your internet speed). Once Multipass has successfully set up the VM, you will
see a message like this in your terminal:

.. code-block:: text

   Launched: test-vm

We can now enter our new VM with this command:

.. code-block:: bash

   $ multipass shell test-vm

Notice that when we run this command, our terminal username and hostname
change to ``ubuntu@test-vm``, which tells us we are now operating inside the
VM. 

We then see a welcome message that looks similar to this (throughout this
tutorial, we will truncate the output for brevity -- removed sections will be
indicated with ``[...]``):

.. code-block:: text

    Welcome to Ubuntu 18.04.6 LTS (GNU/Linux 4.15.0-212-generic x86_64)

     [...]

      System information as of Wed Jun 19 14:17:26 BST 2024

      [...]

    Expanded Security Maintenance for Infrastructure is not enabled.

    16 updates can be applied immediately.
    11 of these updates are standard security updates.
    To see these additional updates run: apt list --upgradable

    109 additional security updates can be applied with ESM Infra.
    Learn more about enabling ESM Infra service for Ubuntu 18.04 at
    https://ubuntu.com/18-04

    [...]

We can see immediately that our virtual machine is not fully up-to-date, with
16 software updates that can be applied, and 103 additional security updates
(available with ESM-Infra). Let's first see which software updates we can
apply by running the command that was suggested in the output:

.. code-block:: bash

   $ apt list --upgradable

This will show us a list of all the packages with available updates, the
current version, and the version we can upgrade to:

.. code-block:: bash

    Listing... Done
    [...]
    python3-update-manager/bionic-updates 1:18.04.12 all [upgradable from: 1:18.04.11.13]
    shim-signed/bionic-updates 1.37~18.04.13+15.7-0ubuntu1 amd64 [upgradable from: 1.37~18.04.11+15.4-0ubuntu9]
    ubuntu-pro-client/bionic-updates 32.3~18.04 amd64 [upgradable from: 27.14.4~18.04]
    update-manager-core/bionic-updates 1:18.04.12 all [upgradable from: 1:18.04.11.13]
    update-notifier-common/bionic-updates 3.192.1.21 all [upgradable from: 3.192.1.19]

One of the packages that needs updating is the ``ubuntu-pro-client``
package, which provides the Pro Client, but it's good practice to always keep
software up-to-date, so let's upgrade all of these packages in our VM:

.. code-block::

   $ sudo apt update && sudo apt upgrade -y

This will install the 16 pending software updates. In the next step, we'll
tackle the 103 security updates.

Check the machine's security status
===================================

We know, since we just updated it, that the package providing the Pro Client
is already installed and up-to-date. So now, let's check on the security status
of our machine:

.. code-block:: bash

   $ pro security-status

After our update in the last section, we should see something that looks like
this in our terminal output:

.. code-block:: text

    518 packages installed:
        518 packages from Ubuntu Main/Restricted repository

    [...]

    This machine is NOT receiving security patches because the LTS period has ended
    and esm-infra is not enabled.
    This machine is NOT attached to an Ubuntu Pro subscription.

    Ubuntu Pro with 'esm-infra' enabled provides security updates for
    Main/Restricted packages until 2028. There are 110 pending security updates.

    [...]

Let's break this down a bit.

The security-status output
--------------------------

.. code-block:: text

    518 packages installed:
        518 packages from Ubuntu Main/Restricted repository

Here, we learn that all 518 installed packages on our system come from the
Ubuntu Main or Restricted repositories. This is not surprising -- we haven't
installed any of our own packages yet! The only packages on the system are
those that shipped with the default Bionic image.

.. code-block:: text

    This machine is NOT receiving security patches because the LTS period has ended
    and esm-infra is not enabled.
    This machine is NOT attached to an Ubuntu Pro subscription.

The message also lets us know that 'esm-infra' is not enabled. **ESM-Infra** is
the Ubuntu Pro service that provides security coverage for packages in Main
and Restricted **after** the initial 5 years of standard support for an LTS. 

.. code-block:: text

    Ubuntu Pro with 'esm-infra' enabled provides security updates for
    Main/Restricted packages until 2028. There are 110 pending security updates.

With ESM-Infra, an LTS system gets a total of 10 years of security coverage for
packages in Main and Restricted. So, although LTS support for Bionic ended in
2023, ``esm-infra`` would cover us until 2028 on this machine -- and we would
get 110 security updates as soon as we enabled it.

What about packages in Universe?
--------------------------------

It's fair to assume that most people will go beyond the default distribution
and also install software from the Universe and Multiverse repositories. We
don't have any of those yet, so let's see what happens if we install a popular
package that comes from Universe, such as Ansible:

.. code-block:: bash
   
   $ sudo apt install ansible -y

We can run ``pro security-status`` again to see what happened:

.. code-block:: text

    555 packages installed:
        550 packages from Ubuntu Main/Restricted repository
        5 packages from Ubuntu Universe/Multiverse repository

    [...]

    Ubuntu Pro with 'esm-infra' enabled provides security updates for
    Main/Restricted packages until 2028. There are 119 pending security updates.

    Ubuntu Pro with 'esm-apps' enabled provides security updates for
    Universe/Multiverse packages until 2028. There is 1 pending security update.

    [...]

We now have 5 packages listed as coming from Universe/Multiverse -- this is
the Ansible package and its dependencies. There are also now 119 security
updates available through ``esm-infra``, so some of the Ansible dependencies
also had security updates.

We can see that ``esm-apps`` has 1 additional security update for Ansible
itself. **ESM-Apps** provides security updates from Canonical for packages in
Universe and Multiverse -- even during the LTS period. This means that newer
Ubuntu releases like 24.04 Noble **also** benefit from Ubuntu Pro coverage.

The updates we get from ``esm-apps`` address critical and high severity
vulnerabilities, and this support is in addition to updates provided by the
Ubuntu Community.

So now we've seen that if we enabled ``esm-infra`` and ``esm-apps``, we would
receive quite a few additional security updates. To enable these services, we
first need to attach to an Ubuntu Pro subscription. 

Attach to a subscription
========================

To attach our VM to a subscription, let's run the following command in our
terminal:

.. code-block:: bash

    $ sudo pro attach

We should see output like this, giving us a link and a code:

.. code-block:: text

    ubuntu@test-vm:~$ sudo pro attach
    Initiating attach operation...

    Please sign in to your Ubuntu Pro account at this link:
    https://ubuntu.com/pro/attach
    And provide the following code: H31JIV

Let's first copy the code (``H31JIV`` in this example, but yours will be
different), then open the link in our browser without closing the terminal
window. Paste or type the code into the "Enter your code" field.

By default, the "Free Personal Token" will be selected in the "Choose a
subscription to attach" field, and we can click on "Submit" to accept this. 

.. note::
   You can safely use one of your free personal tokens for this -- after we
   destroy this VM the token can be re-used.

The attach process will then continue in the terminal window, and after the
authentication is complete we will be presented with the following message:

.. code-block:: text 

    Attaching the machine...
    Enabling default service esm-apps
    Updating Ubuntu Pro: ESM Apps package lists
    Ubuntu Pro: ESM Apps enabled
    Enabling default service esm-infra
    Updating Ubuntu Pro: ESM Infra package lists
    Ubuntu Pro: ESM Infra enabled
    Enabling default service livepatch
    Installing snapd snap
    Installing canonical-livepatch snap
    Canonical Livepatch enabled
    This machine is now attached to 'Ubuntu Pro - free personal subscription'

When the machine has successfully been attached, we also get a summary of
which services are enabled and information about our subscription. This
summary is the same result that you would get if you ran the ``pro status``
command to check on the status of the different Ubuntu Pro services:

.. code-block:: text

    SERVICE          ENTITLED  STATUS       DESCRIPTION
    cc-eal           yes       disabled     Common Criteria EAL2 Provisioning Packages
    cis              yes       disabled     Security compliance and audit tools
    esm-apps         yes       enabled      Expanded Security Maintenance for Applications
    esm-infra        yes       enabled      Expanded Security Maintenance for Infrastructure
    fips             yes       disabled     NIST-certified FIPS crypto packages
    fips-updates     yes       disabled     FIPS compliant crypto packages with stable security updates
    livepatch        yes       warning      Canonical Livepatch service
    ros              yes       disabled     Security Updates for the Robot Operating System
    ros-updates      yes       disabled     All Updates for the Robot Operating System

There are three services NOT disabled by default: ``esm-apps``, ``esm-infra``,
and ``livepatch``. These three services are considered useful for everyone,
and so they are enabled by default when you attach your machine to a
subscription.

Enabling ``esm-apps`` and ``esm-infra`` provides us with access to the
repositories containing the additional security updates we saw earlier.

What about Livepatch?
---------------------

`Livepatch`_ is a service that patches vulnerabilities in the Linux kernel
while the system runs, meaning that we don't need to immediately reboot the
machine to apply these patches.

When Livepatch is enabled, the Livepatch client, ``canonical-livepatch``, is
automatically installed, but what happens next depends on which kernel you are
running. You will either:

* Get all available patches applied to your system automatically, or
* Need to update your kernel before Livepatch can be fully activated.

In our case, the default Bionic image contains an old kernel, so we have a
warning beside ``livepatch`` and the following notice shown below the table:

.. code-block:: text

    NOTICES
    The running kernel has reached the end of its active livepatch window.
    Please upgrade the kernel with apt and reboot for continued livepatch support.

We therefore need to update the kernel before we can feel the benefit of
Livepatch.

Apply our new updates
=====================

Applying the newly available updates is as simple as running the ``update``
and ``upgrade`` commands again:

.. code-block:: bash

   sudo apt update && sudo apt upgrade -y

This may take a few minutes -- we have quite a few updates to install!

Now we can run ``pro security-status`` once more to see a summary of the
results of attaching to our subscription and updating the software:

.. code-block:: text

    559 packages installed:
        554 packages from Ubuntu Main/Restricted repository
        5 packages from Ubuntu Universe/Multiverse repository

    [...]

    This machine is attached to an Ubuntu Pro subscription.

    Main/Restricted packages are receiving security updates from
    Ubuntu Pro with 'esm-infra' enabled until 2028. You have received 121 security
    updates.

    Universe/Multiverse packages are receiving security updates from
    Ubuntu Pro with 'esm-apps' enabled until 2028. You have received 1 security
    update.

The update we did after attaching also updates our kernel to the newer version
(where Livepatch can be used). To boot into the new kernel, we need to restart
the VM. 

To do this, press :kbd:`Ctrl` + :kbd:`D` together to exit the VM, and then
run:

.. code-block:: bash

   multipass restart test-vm

After Multipass has restarted our VM, we can log back into it:

.. code-block:: bash

   multipass shell test-vm

Now if we run ``pro status`` again, we will see that Livepatch no longer has a
warning, and its status is listed as ``enabled``:

.. code-block:: text

    SERVICE          ENTITLED  STATUS       DESCRIPTION
    cc-eal           yes       disabled     Common Criteria EAL2 Provisioning Packages
    cis              yes       disabled     Security compliance and audit tools
    esm-apps         yes       enabled      Expanded Security Maintenance for Applications
    esm-infra        yes       enabled      Expanded Security Maintenance for Infrastructure
    fips             yes       disabled     NIST-certified FIPS crypto packages
    fips-updates     yes       disabled     FIPS compliant crypto packages with stable security updates
    livepatch        yes       enabled      Canonical Livepatch service
    ros              yes       disabled     Security Updates for the Robot Operating System
    ros-updates      yes       disabled     All Updates for the Robot Operating System

When Livepatch is enabled, the Livepatch client automatically installs any
available fixes for high and critical severity vulnerabilities in the kernel
without us needing to specifically ask it to.

If we want to know which vulnerabilities have been patched by the Livepatch
client, we can run:

.. code-block:: bash

   canonical-livepatch status --format yaml

If the kernel is very new, there may not be any patches to apply yet, but we
can always use this command to see what Livepatch has fixed for us.

So, we are now fully up-to-date with all of the software and security updates
for the packages on our VM. But what if we were not using a fresh VM? Let's
consider a scenario that might affect us on our live system.

Checking for vulnerabilities
============================

There are two types of vulnerabilities that could affect a system:
`Common Vulnerabilities and Exposures <cve_>`_ (CVEs) and
`Ubuntu Security Notices <usn_>`_ (USNs).

CVEs are a way to publicly track and catalogue security vulnerabilities in
software. Each is given a unique identifier in the format ``CVE-XXXX-XXXX``.
To learn more about CVEs, check out our
:ref:`explanation of CVEs and USNs <expl-cve-usn>`.
   
We've seen how, just by attaching our Pro subscription and upgrading our
machine, the Pro Client services have taken care of applying the available
fixes for the CVEs that affected our VM. In fact, as long as we upgrade
our machine periodically, these fixes will always be applied after they are
released. The default configuration of ``unattended-upgrades`` runs upgrades
for you daily and includes Pro security updates.

However, there is always a period of time between a CVE or USN being reported
and the fix being released. In this case, we might reasonably want some way to
find out if a vulnerability is affecting our system.

In an upcoming release of the Pro Client, we will have a command that shows us
a list of all CVEs that affect our system, and their status. For now, we can
use the ``pro fix`` command to manually inspect and resolve both CVEs and USNs.

.. note::
   This may be especially of interest to users who need more control over
   their updates!

Now, we have a bit of a problem. We know that our machine is fully up-to-date
and all available fixes have been applied! But, using our VM we can simulate
having a package affected by a known CVE using the Ansible package we installed
earlier. `CVE-2023-5764`_ affected the LTS Bionic version of Ansible, so
let's use this as our test case. We can run the ``pro fix`` command with the
``--dry-run`` flag to inspect the CVE without actually fixing anything, so let
us do just that:

.. code-block:: bash

   sudo pro fix cve-2023-5764 --dry-run   

.. code-block:: text

    WARNING: The option --dry-run is being used.
    No packages will be installed when running this command.
    CVE-2023-5764: Ansible vulnerabilities
     - https://ubuntu.com/security/CVE-2023-5764

    1 affected source package is installed: ansible
    (1/1) ansible:
    A fix is available in Ubuntu Pro: ESM Apps.
    The update is already installed.

    ✔ CVE-2023-5764 is resolved.

As we can see, in the version of Ansible we are running (thanks to Pro) we are
not affected by this CVE. But what happens if we downgrade Ansible to an older
version that **was** affected by it:

.. code-block:: bash

   sudo apt install ansible/bionic-updates -y

This command will install the last LTS update for Ansible in Bionic, which
doesn't have the updates we got from Pro. Now, we can use this command again
to see what happened:

.. code-block:: bash

   sudo pro fix cve-2023-5764 --dry-run   

.. code-block:: text

    WARNING: The option --dry-run is being used.
    No packages will be installed when running this command.
    CVE-2023-5764: Ansible vulnerabilities
     - https://ubuntu.com/security/CVE-2023-5764

    1 affected source package is installed: ansible
    (1/1) ansible:
    A fix is available in Ubuntu Pro: ESM Apps.
    { apt update && apt install --only-upgrade -y ansible }

    ✔ CVE-2023-5764 is resolved.

Now we can see that we **are** affected by a CVE in the Ansible package, and
that the CVE is resolved so we can apply the fix for it. 

The pro fix output
------------------

The output of the ``pro fix`` command has the same structure, whether we are
only inspecting a CVE using ``--dry-run``, or resolving a CVE. It:

* describes the CVE/USN (with a link to its database entry);
* displays the affected package(s);
* the location of a fix (if one is available); and
* at the end, shows if the CVE/USN is fully fixed in the machine.

This is best demonstrated in a ``pro fix`` call that *does* fix a package.

Manually resolve the CVE
------------------------

Now that we've found a package that has a vulnerability, we can fix it using
the ``pro fix`` command on the CVE (without the ``--dry-run`` option):

.. code-block:: bash

    $ sudo pro fix CVE-2023-5764

You will then see the following output:

.. code-block:: text

    CVE-2023-5764: Ansible vulnerabilities
     - https://ubuntu.com/security/CVE-2023-5764

    1 affected source package is installed: ansible
    (1/1) ansible:
    A fix is available in Ubuntu Pro: ESM Apps.
    { apt update && apt install --only-upgrade -y ansible }

      ✔ CVE-2023-5764 is resolved.

.. note::
    We need to run the command with ``sudo`` because it will be installing a
    package on the system.

Also, at the end of the output you can see confirmation that the CVE was fixed
by the command. Just to confirm that the fix was successfully applied, let's
run the ``pro fix`` command again, and we should now see the following:

.. code-block:: text

    CVE-2023-5764: Ansible vulnerabilities
     - https://ubuntu.com/security/CVE-2023-5764

    1 affected source package is installed: ansible
    (1/1) ansible:
    A fix is available in Ubuntu Pro: ESM Apps.
    The update is already installed.

      ✔ CVE-2023-5764 is resolved.

Success!
========

In this tutorial, we have successfully run a Multipass VM and used it to:

- Check on the machine's security status with ``pro security-status``
- Update the software with ``sudo apt update && sudo apt upgrade -y``
- Attach our subscription so we can access ESM-Apps, ESM-Infra, and Livepatch
  using ``sudo pro attach``
- Apply security updates by running ``sudo apt update && sudo apt upgrade -y``
  again (after attaching to our subscription)
- Check the status of the Pro services on the machine with ``pro status``
- Check the fixes applied by Livepatch using
  ``canonical-livepatch status --format yaml``
- Check the status of a CVE using ``pro fix --dry-run``
- And we used ``pro fix`` to resolve it.

Close down the VM
-----------------

When you are finished and want to leave the tutorial, you can shut down the VM
by first pressing :kbd:`Ctrl` + :kbd:`D` to exit it, and then running the
following commands to delete the VM completely:

.. code-block:: bash

   multipass delete test-vm
   multipass purge

We don't need to detach our subscription first. When the VM is deleted and
purged, the token is released and can be used again.

Further reading
---------------

* :ref:`ESM explained <expl-ESM>`: to find out more about ESM-Infra, ESM-Apps
  and the different repositories.
* :ref:`CVES/USNs explained <expl-cve-usn>`: to find out more about CVEs, USNs
  and related USNs.
* :ref:`Which services are for me? <which-services>`: Ubuntu Pro includes a
  wide range of services. Although in this tutorial we've covered the three
  services that are likely to be of interest to most people, you might be
  curious about what else you might find useful. 

Get help
--------

.. Instructions for how to connect with us
.. include:: ../includes/contact.txt

.. LINKS

.. include:: ../links.txt

.. _Multipass: https://multipass.run/
.. _CVE-2023-5764: https://ubuntu.com/security/CVE-2023-5764
