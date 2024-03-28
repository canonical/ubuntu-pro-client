.. _pro-fix-check-cve:

How to Determine if Your System is Affected by a CVE/USN?
*******************************************************

.. include:: ../includes/pro-fix-intro.txt


If you've come across a Common Vulnerabilities and Exposure (CVE) or a Ubuntu Security Notification (USN) and want to check if your Ubuntu system is vulnerable, you can easily check using the `pro fix` command. In this guide we'll show you how to determine if your system is affected by a specific CVE:

..note::
    The `pro fix` command is part of the `pro` package, which is a security tool for Ubuntu systems. If you don't have it installed, you can install it by following the instructions in the `pro` package documentation.

Performing a Dry Run
====================

A dry run allows you to simulate the execution of the ``pro fix`` command without actually making any changes to your system. This is useful for checking if a CVE affects your system and if a fix is available.

Let's see what happens when we perform a dry run with the ``pro fix`` command.

Every ``pro fix`` output has a similar output structure. It:

* describes the CVE/USN;
* displays the affected packages;
* fixes the affected packages; and
* at the end, shows if the CVE/USN is fully fixed in the machine.


To perform a dry run, use the ``--dry-run`` option with the ``pro fix`` command followed by the CVE identifier:

.. code-block:: bash

    $ pro fix --dry-run CVE-XXXX-XXXX

Replace ``CVE-XXXX-XXXX`` with the actual CVE identifier you want to check.

Output of a Dry Run
===================

The output of the dry run will indicate whether your system is affected by the CVE and if a fix is available. Here are some possible scenarios:

CVE does not affect your system
--------------------------------

   .. code-block:: text

       CVE-XXXX-XXXX: Some vulnerability
        - https://ubuntu.com/security/CVE-XXXX-XXXX

       No affected source packages are installed.

       ✔ CVE-XXXX-XXXX does not affect your system.

CVE affects your system, and a fix is available
-----------------------------------------------

   .. code-block:: text

       CVE-XXXX-XXXX: Some vulnerability
        - https://ubuntu.com/security/CVE-XXXX-XXXX

       1 affected source package is installed: package-name
       (1/1) package-name:
       A fix is available in Ubuntu standard updates.
       { apt update && apt install --only-upgrade -y package-name }

       ✔ CVE-XXXX-XXXX can be resolved.

CVE affects your system, but no fix is available
-----------------------------------------------

   .. code-block:: text

       CVE-XXXX-XXXX: Some vulnerability
        - https://ubuntu.com/security/CVE-XXXX-XXXX

       1 affected source package is installed: package-name
       Ubuntu security engineers are investigating this issue.

       ✘ CVE-XXXX-XXXX is not resolved.


Here we see how performing a dry run with the ``pro fix`` command is a quick and safe way to check if your system is affected by a specific CVE and also see if a fix is available.

Success!
==========

We have successfully determined if our system is affected by a specific CVE using the `pro fix` command. If a fix is available, you can proceed to apply the fix by running the command provided in the output.
To learn how to resolve a CVE using the `pro fix` command, refer to the guide on :ref:`How to resolve a CVE/USN? <_pro-fix-resolve-cve>`.

Additional Resources
--------------------

This is not the only scenario where you might want to use ``pro fix``. To find out about the other situations where it can be useful, as well as which options can be used to give you greater control over the command, you can refer to the following guides: 

* In :ref:`Understanding scenarios encountered when using pro fix to solve a CVE/USN <pro-fix-howto>` you can continue learning more about the different scenarios you might encounter and understand the different outputs you will find.
* :ref:`How do I know what the pro fix command would change? <pro-fix-dry-run>` will show you how to use ``pro fix`` in ``--dry-run`` mode to safely simulate the changes before they're applied.
* :ref:`How to skip fixing related USNs <pro-fix-skip-related>` will show you how to only fix a single USN, even if other fixes are available.

.. Instructions for how to connect with us
.. include:: ../includes/contact.txt
