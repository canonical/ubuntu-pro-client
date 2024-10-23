How to interpret the output of pro cve
**************************************

If you suspect that a CVE affects your system and wants to verify
if that is true, you can use the ``pro cve`` command for this.
This command will show you all the related information to a CVE **if** it affects
your Ubuntu release.

For example, let's assume that ``CVE-2022-2286`` affects your system and you run:

.. code-block:: bash

    pro cve CVE-2024-5480

You will see an output similar to this one:

.. code-block:: text

   name:               CVE-2024-5480
   public-url:         https://ubuntu.com/security/CVE-2024-5480
   published-at:       2024-05-26
   cve-cache-date:     2024-11-27
   apt-cache-date:     2024-11-25
   priority:           critical
   cvss-score:         9.8
   cvss-severity:      urgent
   description: |
     Systems with microprocessors utilizing speculative execution and indirect branch   
     prediction may allow unauthorized disclosure of information to an attacker with
     local user access via a side-channel analysis of the data cache.
   notes:
    - mdeslaur> requires sourcing a vim commands file or similar
   affected-packages:
     firefox: available (esm-infra) 1.2.3~esm1
     python3: available (standard)  1.5
     vim:     deferred
   related-usns:
     USN-6841-1: PHP vulnerability
     USN-6839-1: MariaDB vulnerability 


Let's break it down the output of this command. We start by telling you some basic information for
the CVE:

* **name**: The CVE name
* **public-url**: The ubuntu dedicated CVE page
* **published-at**: The published date of the CVE
* **cve-cache-date**: The date of the local CVE datasource cache
* **apt-cache-date**: The last time the APT state was updated in the system
  (i.e. running an apt install operation)
* **priority**: The ubuntu priority for this CVE
* **cvss-score**: The CVSS score of the CVE
* **cvss-severity**: The CVSS severity of the CVE
* **description**: The CVE description
* **notes**: The CVE related notes

The next block is now displaying which installed packages in the machine are affected by the CVE,
in the format:

.. code-block:: text

   affected-packages:
     firefox: available (esm-infra) 1.2.3~esm1
     python3: available (standard)  1.5
     vim:     deferred

If the package has a fix available, we will use the format:

.. code-block:: text

   affected-packages:
     firefox: available (esm-infra) 1.2.3~esm1

This line can be broke down into four distinct fields:

* **name**: The package name
* **status**: The CVE fix status for that package
* **origin**: The CVE fix origin
* **version**: The package version that will fix the CVE for that package

And if the package doesn't have a fix available, we will use the format:

.. code-block:: text

   affected-packages:
     vim:     deferred

Where the line will only contain the package name and the CVE status for it


Finally, we also display the related USNs to the CVE:

.. code-block:: text

   related-usns:
     USN-6841-1: PHP vulnerability
     USN-6839-1: MariaDB vulnerability 


What if the CVE doesn't affect my system ?
==========================================

If the CVE doesn't affect your system, The **affected-packages** field will be displayed like this:

.. code-block:: text

   affected-packages: []

Which means that no installed packages are affected by the CVE.


What if the CVE doesn't affect my Ubuntu release ?
===================================================

If the CVE doesn't affect the Ubuntu release you are running own, that means
that our CVE source data will not contain any information about it. Therefore,
the command will display the following output:

.. code-block:: text

   CVE-2025-26520 doesn't affect Ubuntu 16.04.
   For more information, visit: https://ubuntu.com/security/CVE-2025-26520

In this example, the CVE-2025-26520 doesn't affect the Xenial Ubuntu release (Ubuntu 16.04).
