.. _pro-fix-check-cve:

How to check if a system is affected by a CVE/USN?
**************************************************

.. include:: ../includes/pro-fix-intro.txt


If you've found a `Common Vulnerabilities and Exposure <cve_>`_ (CVEs) and `Ubuntu Security Notice <usn_>`_ (USNs) and want to check if your Ubuntu system is affected by it, you can check using the ``pro fix`` command as we'll show you in this guide.

.. note::
    The ``pro fix`` command is part of the Ubuntu Pro Client (``pro``), which is a security tool for Ubuntu systems. The Ubuntu Pro Client comes pre-installed on every Ubuntu system. You can run ``pro help`` in your terminal window to see a list of the ``pro`` services and commands available.

Perform a "dry run"
===================

A "dry run" lets you simulate running the ``pro fix`` command without actually making any changes to your system. This is useful for checking if a CVE affects your system and whether a fix is available.

Let's see what happens when we perform a dry run with the ``pro fix`` command.

Every ``pro fix`` output has a similar output structure. It:

* describes the CVE/USN;
* displays the affected packages;
* fixes the affected packages; and
* at the end, shows if the CVE/USN is fully fixed in the machine.


To perform a dry run, use the ``--dry-run`` option with the ``pro fix`` command followed by the CVE identifier:

.. code-block:: bash

    pro fix --dry-run CVE-XXXX-XXXX

Replace ``CVE-XXXX-XXXX`` with the actual CVE identifier you want to check.

Output of a "dry run"
=====================

The output of the dry run will indicate whether your system is affected by the CVE and if a fix is available. Here are some possible scenarios:

CVE does not affect your system
--------------------------------

Here, for example, We will choose to fix a CVE that does not affect the system -- for example if you do not have ``MariaDB`` installed and want to check `CVE-2020-15180`_.

.. code-block:: bash

    pro fix --dry-run CVE-2020-15180

You should see an output like this:

.. code-block:: text

    CVE-2020-15180: MariaDB vulnerabilities
     - https://ubuntu.com/security/CVE-2020-15180

    No affected source packages are installed.

    ✔ CVE-2020-15180 does not affect your system.

CVE affects your system, and a fix is available
------------------------------------------------

Let's simulate a scenario where an older package associated with `CVE-2020-25686`_ is installed on the machine.

.. code-block:: bash

    sudo pro fix --dry-run CVE-2020-25686

The output will indicate that the system is affected and a fix is available:

.. code-block:: text

    CVE-2020-25686: Dnsmasq vulnerabilities
     - https://ubuntu.com/security/CVE-2020-25686

    1 affected package is installed: dnsmasq
    (1/1) dnsmasq:
    A fix is available in Ubuntu standard updates.
    { apt update && apt install --only-upgrade -y dnsmasq }

    ✔ CVE-2020-25686 is resolved.


CVE affects your system, but no fix is available
-------------------------------------------------

Some CVEs/USNs do not have a fix released yet. When that happens, the dry run output will let you know.
This is example output created in the past, for which there
might be fixes later on. To create this scenario we installed a
known affected package with no fix (at the time) and then checked for an
available fix:

.. code-block:: bash

    sudo apt-get install -y expat=2.1.0-7 swish-e matanza ghostscript

Now, we can confirm that there is no fix by running the following command:

.. code-block:: bash

    pro fix --dry-run CVE-2017-9233

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

CVE that requires a Pro service
-------------------------------

Assuming you have attached to a Pro subscription, when running the ``pro fix`` command
you may see that the service required to fix the issue is not enabled. In this situation,
``pro fix`` will also prompt you to enable that service.

For example, if you want to fix the issue CVE-2023-1523 which requires the Pro service ``esm-infra``
and you run the following command:

.. code-block:: bash

    sudo pro fix --dry-run CVE-2023-1523

You will see the following output (if you type :kbd:`E` to enable the service when prompted):

.. code-block:: text

    CVE-2023-1523: snapd vulnerability
     - https://ubuntu.com/security/CVE-2023-1523

    1 affected source package is installed: snapd
    (1/1) snapd:
    A fix is available in Ubuntu Pro: ESM Infra.
    The update is not installed because this system does not have
    esm-infra enabled.

    Choose: [E]nable esm-infra [C]ancel
    > E
    { pro enable esm-infra }
    Updating Ubuntu Pro: ESM Infra package lists
    Ubuntu Pro: ESM Infra enabled
    { apt update && apt install --only-upgrade -y snapd ubuntu-core-launcher }

    ✔ CVE-2023-1523 is resolved.

We can observe that the required service was enabled and ``pro fix`` was able
to successfully upgrade the affected package.

Here we see how performing a dry run with the ``pro fix`` command is a quick and safe way to check if your system is affected by a specific CVE and also see if a fix is available.

Success!
========

Here we see how performing a dry run with the ``pro fix`` command is a quick and safe way to check if your system is affected by a specific CVE and also see if a fix is available. If a fix is available, you can apply the fix by running the command provided in the output.
To learn how to resolve a CVE using the ``pro fix`` command, refer to the guide on :ref:`How to resolve a CVE/USN <pro-fix-resolve-cve>`.

Additional resources
--------------------

This is not the only scenario where you might want to use ``pro fix``. To find out about the other situations where it can be useful, as well as which options can be used to give you greater control over the command, you can refer to the following guides: 

* In :ref:`Understanding scenarios encountered when using pro fix to solve a CVE/USN <pro-fix-howto>` you can continue learning more about the different scenarios you might encounter and understand the different outputs you will find.
* :ref:`How do I know what the pro fix command would change? <pro-fix-dry-run>` will show you how to use ``pro fix`` in ``--dry-run`` mode to safely simulate the changes before they're applied.
* :ref:`How to skip fixing related USNs <pro-fix-skip-related>` will show you how to only fix a single USN, even if other fixes are available.

.. Instructions for how to connect with us
.. include:: ../includes/contact.txt

.. LINKS

.. include:: ../links.txt

.. _CVE-2020-15180: https://ubuntu.com/security/CVE-2020-15180
.. _CVE-2020-25686: https://ubuntu.com/security/CVE-2020-25686
