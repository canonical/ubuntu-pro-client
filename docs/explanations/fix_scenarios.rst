.. _pro-fix-howto:

Scenarios encountered using ``pro fix`` to solve a CVE/USN
**********************************************************

.. Into "what is pro fix" shared with the related tutorial
.. include:: ../includes/pro-fix-intro.txt

This howto will go a bit deeper and after introducing the ``pro fix``
command it will go in more details about the differen scenarios you may
encounter using ``pro fix``.

.. note::

   If instead you look for a simpler guided tutorial to get started with
   ``pro fix`` please start at
   :ref:`Use pro fix to solve a CVE/USN <pro-fix-tutorial>`.


Use ``pro fix``
===============

First, let's see what happens to your system when ``pro fix`` runs. We will
choose to fix a CVE that does not affect the VM -- in this case,
`CVE-2020-15180`_. This CVE addresses security issues for the ``MariaDB``
package, which is not installed on the system.

Let's first confirm that it doesn't affect the system by running this command:

.. code-block:: bash

    $ pro fix CVE-2020-15180

You should see an output like this:

.. code-block:: text

    CVE-2020-15180: MariaDB vulnerabilities
    https://ubuntu.com/security/CVE-2020-15180

    No affected source packages are installed.

    ✔ CVE-2020-15180 does not affect your system.

Every ``pro fix`` output has a similar output structure. It:

* describes the CVE/USN;
* displays the affected packages;
* fixes the affected packages; and
* at the end, shows if the CVE/USN is fully fixed in the machine.

.. # The basic case is shared between Howto and Tutorial
.. include:: ../includes/pro-fix-simple-case.txt

CVE/USN without a released fix
==============================

Some CVEs/USNs do not have a fix released yet. When that happens, ``pro fix``
will let you know! Before we reproduce this scenario, let us first install a
package that we know has no fix available by running:

.. code-block:: bash

    $ sudo apt-get install -y expat=2.1.0-7 swish-e matanza ghostscript

Now, we can confirm that there is no fix by running the following command:

.. code-block:: bash

    $ pro fix CVE-2017-9233

You will see the following output:

.. code-block:: text

    CVE-2017-9233: Coin3D vulnerability
    - https://ubuntu.com/security/CVE-2017-9233

    3 affected source packages are installed: expat, matanza, swish-e
    (1/3, 2/3) matanza, swish-e:
    Ubuntu security engineers are investigating this issue.
    (3/3) expat:
    A fix is available in Ubuntu standard updates.
    { apt update && apt install --only-upgrade -y expat }

    2 packages are still affected: matanza, swish-e
    ✘ CVE-2017-9233 is not resolved.

As we can see, we are informed by ``pro fix`` that some packages do not have a
fix available. In the last line, we can also see that the CVE is not resolved.

CVE/USN that require an Ubuntu Pro subscription
===============================================

Some package fixes can only be installed when the machine is attached to an
Ubuntu Pro subscription. When that happens, ``pro fix`` will tell you that.
To see an example of this scenario, you can run the following fix command:

.. code-block:: bash

    $ sudo pro fix USN-5079-2

The command will prompt you for a response, like this:

.. code-block:: text

    USN-5079-2: curl vulnerabilities
    Associated CVEs:
    https://ubuntu.com/security/CVE-2021-22946
    https://ubuntu.com/security/CVE-2021-22947

    Fixing requested USN-5079-2
    1 affected package is installed: curl
    (1/1) curl:
    A fix is available in Ubuntu Pro: ESM Infra.
    The update is not installed because this system is not attached to a
    subscription.

    Choose: [S]ubscribe at ubuntu.com [A]ttach existing token [C]ancel
    > 

We can see that the prompt is asking for an Ubuntu Pro subscription token. Any
user with a Ubuntu One account is entitled to a free personal token to use with
Ubuntu Pro. 

If you choose the ``Subscribe`` option on the prompt, the command will ask you
to go to the `Ubuntu Pro portal <Pro_>`_. In the portal, you can get a free
subscription token by logging in with your "Single Sign On" (SSO) credentials;
the same credentials you use to log into https://login.ubuntu.com.

After getting your Ubuntu Pro token, you can hit :kbd:`Enter` on the prompt
and it will ask you to provide the token you just obtained. After entering the
token you should now see the following output:

.. code-block:: text

    USN-5079-2: curl vulnerabilities
    Associated CVEs:
    https://ubuntu.com/security/CVE-2021-22946
    https://ubuntu.com/security/CVE-2021-22947

    1 affected package is installed: curl
    (1/1) curl:
    A fix is available in Ubuntu Pro: ESM Infra.
    The update is not installed because this system is not attached to a
    subscription.

    Choose: [S]ubscribe at ubuntu.com [A]ttach existing token [C]ancel
    >S
    Open a browser to: https://ubuntu.com/pro
    Hit [Enter] when subscription is complete.
    Enter your token (from https://ubuntu.com/pro) to attach this system:
    > TOKEN
    { pro attach TOKEN }
    Enabling default service esm-infra
    Updating package lists
    Ubuntu Pro: ESM Infra enabled
    This machine is now attached to 'SUBSCRIPTION'

    SERVICE       ENTITLED  STATUS    DESCRIPTION
    cis           yes       disabled  Center for Internet Security Audit Tools
    esm-infra     yes       enabled   Expanded Security Maintenance for Infrastructure
    fips          yes       n/a       NIST-certified core packages
    fips-updates  yes       n/a       NIST-certified core packages with priority security updates
    livepatch     yes       n/a       Canonical Livepatch service

    NOTICES
    Operation in progress: pro attach

    Enable services with: pro enable <service>

                    Account: Ubuntu Pro Client Test
            Subscription: SUBSCRIPTION
                Valid until: 9999-12-31 00:00:00+00:00
    Technical support level: essential
    { apt update && apt install --only-upgrade -y curl libcurl3-gnutls }
    ✔ USN-5079-2 is resolved.

    Found related USNs:
    - USN-5079-1

    Fixing related USNs:
    - USN-5079-1
    No affected source packages are installed.

    ✔ USN-5079-1 does not affect your system.

    Summary:
    ✔ USN-5079-2 [requested] is resolved.
    ✔ USN-5079-1 [related] does not affect your system.

We can see that this command also fixed the related USN **USN-5079-1**.
If you want to learn more about related USNs, refer to
:ref:`our explanation guide<related-usns>`

Finally, we can see that that the attach command was successful, which can be
verified by the status output we see when executing the command. Additionally,
we observe that the USN is indeed fixed, which you can confirm by running the
``pro fix`` command again:

.. code-block:: text

    USN-5079-2: curl vulnerabilities
    Associated CVEs:
    https://ubuntu.com/security/CVE-2021-22946
    https://ubuntu.com/security/CVE-2021-22947

    1 affected package is installed: curl
    (1/1) curl:
    A fix is available in Ubuntu Pro: ESM Infra.
    The update is already installed.

    ✔ USN-5079-2 is resolved.

.. note:: 

    Even though we are not covering this scenario here, if you have an expired
    contract, ``pro fix`` will detect that and prompt you to attach a new token
    for your machine.

CVE/USN that require a Ubuntu Pro service
=========================================

Now, let's assume that you have attached to an Ubuntu Pro subscription, but
when running ``pro fix``, the required service that fixes the issue is not
enabled. In that situation, ``pro fix`` will also prompt you to enable that
service.

To confirm that, run the following command to disable ``esm-infra``:

.. code-block:: bash

    $ sudo pro disable esm-infra

Now, you can run the following command:

.. code-block:: bash

    $ sudo pro fix CVE-2021-44731

And you should see the following output (if you type :kbd:`E` when prompted):

.. code-block:: text

    CVE-2021-44731: snapd vulnerabilities
    https://ubuntu.com/security/CVE-2021-44731

    1 affected package is installed: snapd
    (1/1) snapd:
    A fix is available in Ubuntu Pro: ESM Infra.
    The update is not installed because this system does not have
    esm-infra enabled.

    Choose: [E]nable esm-infra [C]ancel
    > E
    { pro enable esm-infra }
    One moment, checking your subscription first
    Updating package lists
    Ubuntu Pro: ESM Infra enabled
    { apt update && apt install --only-upgrade -y ubuntu-core-launcher snapd }

    ✔ CVE-2021-44731 is resolved.

We can observe that the required service was enabled and ``pro fix`` was able
to successfully upgrade the affected package.

CVEs/USNs that require a reboot
===============================

When running the ``pro fix`` command, sometimes we can install a package that
requires a system reboot to complete. The ``pro fix`` command can detect that
and will inform you about it.

You can confirm this by running the following fix command:

.. code-block:: bash

    $ sudo pro fix CVE-2022-0778

Then you will see the following output:

.. code-block:: text

    CVE-2022-0778: OpenSSL vulnerability
    https://ubuntu.com/security/CVE-2022-0778

    1 affected package is installed: openssl
    (1/1) openssl:
    A fix is available in Ubuntu Pro: ESM Infra.
    { apt update && apt install --only-upgrade -y libssl1.0.0 openssl }
    A reboot is required to complete fix operation.

    ✘ CVE-2022-0778 is not resolved.

If we reboot the machine and run the command again, you will see that it is
indeed fixed:

.. code-block:: text

    CVE-2022-0778: OpenSSL vulnerability
    https://ubuntu.com/security/CVE-2022-0778

    1 affected package is installed: openssl
    (1/1) openssl:
    A fix is available in Ubuntu Pro: ESM Infra.
    The update is already installed.

    ✔ CVE-2022-0778 is resolved.

Partially resolved CVEs/USNs
============================

Finally, you might run a ``pro fix`` command that only fixes some of the
affected packages. This happens when only a subset of the packages have
available updates to fix for that CVE/USN.

In this case, ``pro fix`` will tell you which package(s) it can or cannot fix.
But first, let's install a package so we can run ``pro fix`` to demonstrate
this scenario.

.. code-block:: bash

    $ sudo apt-get install expat=2.1.0-7 swish-e matanza ghostscript

Now, you can run the following command:

.. code-block:: bash

    $ sudo pro fix CVE-2017-9233

And you will see the following output:

.. code-block:: text

    CVE-2017-9233: Expat vulnerability
    https://ubuntu.com/security/CVE-2017-9233

    3 affected packages are installed: expat, matanza, swish-e
    (1/3, 2/3) matanza, swish-e:
    Sorry, no fix is available.
    (3/3) expat:
    A fix is available in Ubuntu standard updates.
    { apt update && apt install --only-upgrade -y expat }
    2 packages are still affected: matanza, swish-e

    ✘ CVE-2017-9233 is not resolved.

We can see that two packages, ``matanza`` and ``swish-e``, don't have any fixes
available, but there is one for ``expat``. So, we install the fix for ``expat``
and at the end of the report we can see that some packages are still affected.

As before, we can also observe that in this scenario we mark the CVE/USN as not
resolved.

Success!
========

Congratulations! You successfully ran a Multipass VM and used it to encounter
and resolve the main scenarios that you might find when you run ``pro fix``.

.. Instructions for closing down and deleting the VM
.. include:: ./common/shutdown-vm.txt

Next steps
----------

You have learned about the various scenarios that ``pro fix`` might encounter
to be ready to undertand what is happening when using it in a variety of
situations.

There are further options to control what exactly will happen when
running ``pro fix``, read about them in:

* :ref:`How to know what the fix command would change? <pro-fix-dry-run>`
* :ref:`How to skip fixing related USNs <pro-fix-skip-related>`

.. Instructions for how to connect with us
.. include:: ../includes/contact.txt

.. LINKS

.. include:: ../links.txt

.. _CVE-2020-15180: https://ubuntu.com/security/CVE-2020-15180
.. _CVE-2020-25686: https://ubuntu.com/security/CVE-2020-25686
