.. _pro-fix-resolve-cve:

How to resolve a specific CVE or USN
************************************

In this guide, we will introduce the ``pro fix`` command and show how you can use it to resolve CVEs/USNs.

.. note::

   If you want a simpler guide to get started with ``pro fix``, start with
   :ref:`our security features tutorial <security-tutorial>`.
   You can use the same VM-based environment created in that tutorial
   to recreate the output shown below yourself. If you have already completed
   the tutorial, you may want to :ref:`skip this section <CVE-no-fix>`.

Use ``pro fix``
===============

First, let's see what happens to your system when ``pro fix`` runs. 
Every ``pro fix`` output has a similar output structure. It:

* describes the CVE/USN;
* displays the affected packages;
* fixes the affected packages; and
* at the end, shows if the CVE/USN is fully fixed in the machine.

.. # The basic case is shared between Howto and Tutorial
.. include:: ../includes/pro-fix-simple-case.txt

There might be other cases which you might encounter when using ``pro fix`` to resolve a CVE/USN. You can learn more about these cases in the guide detailing :ref:`Common scenarios encountered when using pro fix to solve a CVE/USN <pro-fix-howto>`.

Additional resources
--------------------

This is not the only scenario where you might want to use ``pro fix`` . To find out about the other situations where it can be useful, as well as which options can be used to give you greater control over the command, you can refer to the following guides: 

* :ref:`How do I know what the pro fix command would change? <pro-fix-dry-run>` will show you how to use ``pro fix`` in ``--dry-run`` mode to safely simulate the changes before they're applied.
* :ref:`How to skip fixing related USNs <pro-fix-skip-related>` will show you how to only fix a single USN, even if other fixes are available.

.. Instructions for how to connect with us
.. include:: ../includes/contact.txt

.. LINKS

.. include:: ../links.txt

.. _CVE-2020-15180: https://ubuntu.com/security/CVE-2020-15180
.. _CVE-2020-25686: https://ubuntu.com/security/CVE-2020-25686
.. _Pro_: https://ubuntu.com/pro

