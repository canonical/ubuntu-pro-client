.. NOTES
.. Need to test these steps in the next session due to livepatch reporting
.. "upgrade required on 24/6" - need to check what the warning message will be. 

.. AIM
.. - Demonstrate the value of Ubuntu Pro for all users (free or paid).
.. - Encourage people to use/explore it.
.. - Help them understand how it benefits them.

Exploring your system's security with Pro
*****************************************

Whether you're running a newer Ubuntu LTS release, or you're on a version at
the end of its standard support period, you are probably curious about the
security support that Ubuntu Pro can provide.

In this tutorial, we will set up a virtual machine (VM) and use it to explore
some of the security-related services and commands available to all users.
We will see how you can use them to keep your system safer and more secure.

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
your internet speed). Once it has successfully set up the VM, you will see
a message like this in your terminal:

.. code-block:: text

   Waiting for initialization to complete |
   Launched: test-vm

We can now enter our new VM with this command:

.. code-block:: bash

   $ multipass shell test-vm

Notice that when we run this command, our terminal username and hostname
change to ``ubuntu@test-vm``, which indicates that we are now operating
inside the VM. 

We then see a welcome message that looks similar to this (truncated for
brevity, removed sections indicated with ``[...]``):

.. code-block:: text

    Welcome to Ubuntu 18.04.6 LTS (GNU/Linux 4.15.0-212-generic x86_64)

     [...]

      System information as of Wed Jun 19 14:17:26 BST 2024

      [...]

    Expanded Security Maintenance for Infrastructure is not enabled.

    16 updates can be applied immediately.
    11 of these updates are standard security updates.
    To see these additional updates run: apt list --upgradable

    103 additional security updates can be applied with ESM Infra.
    Learn more about enabling ESM Infra service for Ubuntu 18.04 at
    https://ubuntu.com/18-04

    [...]

We can see immediately that our virtual machine is not fully up-to-date, with
16 software updates that can be applied, and 103 additional security updates
(available with ESM-Infra). Let's first see which software updates we can
apply by running the following command:

.. code-block:: bash

   $ apt list --upgradable

This will show us a list of all the packages with available updates, the
current version, and the version we can upgrade to (once again truncated for
brevity):

.. code-block:: bash

    Listing... Done
    [...]
    python3-update-manager/bionic-updates 1:18.04.12 all [upgradable from: 1:18.04.11.13]
    shim-signed/bionic-updates 1.37~18.04.13+15.7-0ubuntu1 amd64 [upgradable from: 1.37~18.04.11+15.4-0ubuntu9]
    ubuntu-advantage-tools/bionic-updates 32.3~18.04 amd64 [upgradable from: 27.14.4~18.04]
    update-manager-core/bionic-updates 1:18.04.12 all [upgradable from: 1:18.04.11.13]
    update-notifier-common/bionic-updates 3.192.1.21 all [upgradable from: 3.192.1.19]

One of the packages that needs updating is the ``ubuntu-advantage-tools``
package, which provides the Pro Client, but it's good practice to always keep
software up-to-date, so let's update all of these packages in our VM:

.. code-block::

   $ sudo apt update && sudo apt upgrade

This will install the 16 software updates, but not the 103 security updates.

Check the machine's security status
===================================

Since we know from our previous step that the Pro Client is already installed,
and that it's up-to-date. So, let's now check on the security status of our
machine.

.. code-block:: bash

   $ pro security-status

After our update in the last section, we should see something that looks like
this in our terminal output:

.. code-block:: text

    518 packages installed:
        518 packages from Ubuntu Main/Restricted repository

    To get more information about the packages, run
        pro security-status --help
    for a list of available options.

    This machine is NOT receiving security patches because the LTS period has ended
    and esm-infra is not enabled.
    This machine is NOT attached to an Ubuntu Pro subscription.

    Ubuntu Pro with 'esm-infra' enabled provides security updates for
    Main/Restricted packages until 2028. There are 104 pending security updates.

    Try Ubuntu Pro with a free personal subscription on up to 5 machines.
    Learn more at https://ubuntu.com/pro

Understanding the output
------------------------

Here, we learn that all 518 installed packages on our system come from the
Ubuntu Main or Restricted repositories. This is not surprising if we recall
that this is a fresh VM and we haven't installed any packages ourselves yet.
The only packages on the system are those that shipped with the Bionic image.

The message also lets us know that ``esm-infra is not enabled``. ESM-Infra is
the Ubuntu Pro service that provides security coverage for packages in Main
and Restricted (after the 5 years standard support for an LTS).

However, most users also install software from the Universe repository, which
is not covered by Canonical except through a Pro subscription (even during the
LTS period). So let's see what happens if we install a popular package that
comes from Universe, such as Ansible:

.. code-block:: bash
   
   $ sudo apt install ansible

And now let's run ``pro security-status`` again to see how the output changes
(truncated to remove the parts that remained the same):

.. code-block:: text

    555 packages installed:
        550 packages from Ubuntu Main/Restricted repository
        5 packages from Ubuntu Universe/Multiverse repository

    [...]

    Ubuntu Pro with 'esm-infra' enabled provides security updates for
    Main/Restricted packages until 2028. There are 113 pending security updates.

    Ubuntu Pro with 'esm-apps' enabled provides security updates for
    Universe/Multiverse packages until 2028. There is 1 pending security update.

    [...]

We now have 5 packages listed as coming from Universe/Multiverse -- this is
the Ansible package and its dependencies.

We can also see that ESM-Apps would give us 1 additional security update for
this package. ESM-Apps provides security updates from Canonical for packages
in Universe/Multiverse -- even during the LTS period. This means that on your
live system, you can still benefit from ESM-Apps coverage even if your system
is still covered by LTS support. These updates are additional to patches
you would receive for Universe packages from the Ubuntu Community.

Attach to a subscription
========================

So, as we've seen, if we enable ``esm-infra`` and ``esm-apps``, we would
receive a number of additional security updates. To enable these services, we
first need to attach to an Ubuntu Pro subscription. 

To attach the VM to a subscription, let's run the following command in our
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

We need to open the link in our browser (without closing the terminal window).

In the "Enter your code" field, copy and paste the code shown in the terminal.
By default, the "Free Personal Token" will be selected in the "Choose a
subscription to attach" field, and we can click on "Submit" to accept this. 

.. note::
   You can safely use one of your free personal tokens for this -- after we
   close down this VM the token can be re-used.

The attach process will then continue in the terminal window, and once the
authentication is completed we will eventually be presented with the following
message:

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
    livepatch        yes       enabled      Canonical Livepatch service
    ros              yes       disabled     Security Updates for the Robot Operating System
    ros-updates      yes       disabled     All Updates for the Robot Operating System

We might notice that three services are already enabled:
``esm-apps``, ``esm-infra`` and ``livepatch``. These services are considered
useful for everyone, and so they are enabled automatically.

Enabling ``esm-apps`` and ``esm-infra`` provides us with access to the
additional security updates we saw earlier, so we can run our upgrade commands
once more:

.. code-block:: bash

   sudo apt update && sudo apt upgrade

This will install and apply the security updates that we were missing.

What happens when Livepatch is enabled
======================================

`Livepatch`_ is a service that patches vulnerabilities in the Linux kernel
while the system runs, meaning that we don't need to immediately reboot the
machine to apply these patches.

.. tip::
   Common Vulnerabilities and Exposures (CVEs) are a way to publicly track
   and catalogue security vulnerabilities in software. Each is given a unique
   identifier in the format CVE-XXXX-XXXX. To learn more about CVEs, check
   out our :ref:`explanation of CVEs and USNs <expl-cve-usn>`.

When Livepatch was enabled, the Livepatch client was installed automatically,
and all available patches for high and critical severity CVEs were
seamlessly applied -- and crucially, we didn't need to restart or reboot
anything!

We can see what fixes Livepatch applied for us using the following command:

.. code-block:: bash

   $ canonical-livepatch status --format yaml

Specifying the ``yaml`` format lets us see the details of exactly which CVEs
have been automatically patched.

.. code-block:: yaml

    client-version: 10.8.3
    machine-id: [...]
    architecture: amd64
    cpu-model: [...]
    last-check: 2024-06-20T09:05:18+01:00
    boot-time: 2024-06-19T13:14:30Z
    uptime: 19h19m56s
    status:
    - kernel: 4.15.0-212.223-generic
      running: true
      livepatch:
        checkState: checked
        patchState: applied
        version: "102.1"
        fixes: |-
          * CVE-2023-31436
          * CVE-2023-34319
          * CVE-2023-3611
          * CVE-2023-3776
          * CVE-2023-40283
          * CVE-2023-42752
          * CVE-2023-42753
          * CVE-2023-4622
          * CVE-2023-4623
          * CVE-2023-4881
          * CVE-2023-51781
          * CVE-2023-6932
          * CVE-2023-7192
          * CVE-2024-1086
      supported: supported
      upgradeRequiredDate: "2024-06-23"
    tier: updates
    cloud-enabled:
      cloud-enabled: true
      cloud: multipass
      region: ""
      az: ""

.. note::
   When you are running Livepatch on a newer machine, such as your live system,
   you may not receive as many updates in one go. Bionic runs on an old kernel
   so we had more patches available to our new VM.

If we would like more information about these CVEs, we can use the ``verbose``
flag instead:

.. code-block:: bash

   $ canonical-livepatch status --verbose

And we will see a text summary of what each of them is about (output
truncated):

.. code-block:: text

    [...]
    fixes:
      * cve-2023-31436
        Gwangun Jung discovered that the Quick Fair Queueing scheduler 
        implementation in the Linux kernel contained an out-of-bounds write 
        vulnerability. A local attacker could use this to cause a denial of 
        service (system crash) or possibly execute arbitrary code.
      * cve-2023-34319
        Ross Lagerwall discovered that the Xen netback backend driver in the 
        Linux kernel did not properly handle certain unusual packets from a 
        paravirtualized network frontend, leading to a buffer overflow. An 
        attacker in a guest VM could use this to cause a denial of service 
        (host system crash) or possibly execute arbitrary code.
      * cve-2023-3611
        It was discovered that the Quick Fair Queueing network scheduler 
        implementation in the Linux kernel contained an out-of-bounds write 
        vulnerability. A local attacker could use this to cause a denial of 
        service (system crash) or possibly execute arbitrary code.
      [...] 

So, simply by attaching to a subscription, we have immediate, automatic
security coverage for our kernel. We didn't need to apply the patches, or
reboot the system for the fixes to be applied.

Now we can check on the security status of our machine once more by running
``pro security-status`` again:

.. code-block:: text

    555 packages installed:
        550 packages from Ubuntu Main/Restricted repository
        5 packages from Ubuntu Universe/Multiverse repository

    [...]

    This machine is attached to an Ubuntu Pro subscription.

    Main/Restricted packages are receiving security updates from
    Ubuntu Pro with 'esm-infra' enabled until 2028. You have received 115 security
    updates.

    Universe/Multiverse packages are receiving security updates from
    Ubuntu Pro with 'esm-apps' enabled until 2028. You have received 1 security
    update.

We are now fully up-to-date with all of the software and security updates for
the packages on our VM, and Livepatch has taken care of the kernel updates
for us.

But what about the case where we are not using a fresh VM? Let's now consider
a scenario that might affect our live system.

CVEs, USNs, and pro fix
=======================

There are two types of vulnerabilities that could affect your system: 
`Common Vulnerabilities and Exposures <cve_>`_ (CVEs, as we've already seen)
and `Ubuntu Security Notices <usn_>`_ (USNs). The Pro Client can be used to
inspect and resolve both types using the ``pro fix`` command.

Inspecting a CVE
----------------

But how do you know if you're affected by a CVE or USN?
[[ how to know if you're affected ]]

[[vulnerability show -> doesn't exist yet, will in 4 months or so. ]]

[[ use ``pro fix CVE-XXXX-XXXX`` with the ``--dry-run`` flag ]]

.. code-block:: bash

   $ pro fix cve-2024-1086 --dry-run

[[find a cve that exists in bionic free, but is fixed in bionic pro]]
[[so before we attach we would run pro fix (whatever cve dry run) and it would tell you that it affects your system]]

Understanding the output
------------------------

The output of the ``pro fix`` command has the same structure, whether you are
only inspecting a CVE using ``--dry-run``, or resolving a CVE. It:

* describes the CVE/USN;
* displays the affected package(s);
* fixes the affected package(s); and
* at the end, shows if the CVE/USN is fully fixed in the machine.

This is best demonstrated in a ``pro fix`` call that *does* fix a package.

Resolving a CVE
---------------

[[Therefore let us install an older package on the VM that we know is associated
with `CVE-2020-25686`_. You can install the package by running these commands:

.. code-block:: bash

    $ sudo apt update
    $ sudo apt install dnsmasq=2.75-1

Now, let's run ``pro fix`` on the CVE:

.. code-block:: bash

    $ sudo pro fix CVE-2020-25686

You will then see the following output:

.. code-block:: text

    CVE-2020-25686: Dnsmasq vulnerabilities
     - https://ubuntu.com/security/CVE-2020-25686

    1 affected package is installed: dnsmasq
    (1/1) dnsmasq:
    A fix is available in Ubuntu standard updates.
    { apt update && apt install --only-upgrade -y dnsmasq }

    ✔ CVE-2020-25686 is resolved.

.. note::
    We need to run the command with ``sudo`` because it will be installing a
    package on the system.

Whenever ``pro fix`` has a package to upgrade, it follows a consistent
structure and displays the following, in this order:

1. The affected package
2. The availability of a fix
3. The location of the fix, if one is available
4. The command that will fix the issue

Also, at the end of the output you can see confirmation that the CVE was fixed
by the command. Just to confirm that the fix was successfully applied, let's
run the ``pro fix`` command again, and we should now see the following:

.. code-block:: text

    CVE-2020-25686: Dnsmasq vulnerabilities
     - https://ubuntu.com/security/CVE-2020-25686

    1 affected package is installed: dnsmasq
    (1/1) dnsmasq:
    A fix is available in Ubuntu standard updates.
    The update is already installed.

    ✔ CVE-2020-25686 is resolved.



Success!
========

In this tutorial, we have successfully run a Multipass VM and used it to:

- Check on the machine's security status with ``pro security-status``
- Update the software with ``sudo apt update && sudo apt upgrade``
- Access ESM-Apps, ESM-Infra, and Livepatch using ``sudo pro attach``
- Applied security updates by running ``sudo apt update && sudo apt upgrade``
  with ESM-Apps and ESM-Infra enabled
- Checked the status of the Pro services on the machine with ``pro status``
- And we've used ``pro fix --dry-run`` to check the status of a CVE and used
  ``pro fix`` to resolve it.

.. Instructions for closing down and deleting the VM
.. include:: ./common/shutdown-vm.txt

Further reading
---------------

* ESM explained
* CVES/USNs explained
* What services are for me?

* In :ref:`Understanding scenarios encountered when using pro fix to solve a CVE/USN <pro-fix-howto>` you can continue using the test environment you created here to explore different scenarios you might encounter and understand the different outputs you will find.
* :ref:`How do I know what the pro fix command would change? <pro-fix-dry-run>` will show you how to use ``pro fix`` in ``--dry-run`` mode to safely simulate the changes before they're applied.
* :ref:`How to skip fixing related USNs <pro-fix-skip-related>` will show you how to only fix a single USN, even if other fixes are available.

.. Instructions for how to connect with us
.. include:: ../includes/contact.txt

.. LINKS

.. include:: ../links.txt

.. _CVE-2020-15180: https://ubuntu.com/security/CVE-2020-15180
.. _CVE-2020-25686: https://ubuntu.com/security/CVE-2020-25686



.. LINKS
.. _Multipass: https://multipass.run/
