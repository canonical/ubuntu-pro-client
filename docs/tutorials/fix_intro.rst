.. _pro-fix-tutorial:

Use ``pro fix`` to solve a CVE/USN
**********************************

.. Why we use Multipass + command to install it
.. include:: ../includes/pro-fix-intro.txt

In this tutorial, we will introduce the ``pro fix`` command and guide
you through a simple example of using it to solve a CVE/USN.

There might be more scenarios that you may encounter using ``pro fix``,
but those are distracting from this tutorial and therefore available
in the separate
:ref:`How to Understand scenarios encountered using pro fix to solve a CVE/USN <pro-fix-howto>`.

.. Why we use Multipass + command to install it
.. include:: ./common/install-multipass.txt

.. Commands for launching and updating a Xenial VM
.. include:: ./common/create-vm.txt


Use ``pro fix``
===============

Every ``pro fix`` output has a similar output structure. It:

* describes the CVE/USN;
* displays the affected packages;
* fixes the affected packages; and
* at the end, shows if the CVE/USN is fully fixed in the machine.

.. # The basic case is shared between Explanation and Tutorial
.. include:: ../includes/pro-fix-simple-case.txt

Success!
========

Congratulations! You successfully ran a Multipass VM and used it to encounter
and resolve a CVE by using ``pro fix``.

.. Instructions for closing down and deleting the VM
.. include:: ./common/shutdown-vm.txt

Next steps
----------

We have successfully encountered and resolved the main scenarios that you might
find when you run ``pro fix``.

This is not the only scenario where you might want to use ``pro fix``. To find out about the other situations where it can be useful, as well as which options can be used to give you greater control over the command, you can refer to the following guides: 

* In :ref:`Understanding scenarios encountered when using pro fix to solve a CVE/USN <pro-fix-howto>` you can continue using the test environment you created here to explore different scenarios you might encounter and understand the different outputs you will find.
* :ref:`How do I know what the pro fix command would change? <pro-fix-dry-run>` will show you how to use ``pro fix`` in ``--dry-run`` mode to safely simulate the changes before they're applied.
* :ref:`How to skip fixing related USNs <pro-fix-skip-related>` will show you how to only fix a single USN, even if other fixes are available.

.. Instructions for how to connect with us
.. include:: ../includes/contact.txt

.. LINKS

.. include:: ../links.txt

.. _CVE-2020-15180: https://ubuntu.com/security/CVE-2020-15180
.. _CVE-2020-25686: https://ubuntu.com/security/CVE-2020-25686
