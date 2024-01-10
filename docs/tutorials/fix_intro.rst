.. _pro-fix-tutorial:

Use ``pro fix`` to solve a CVE/USN
**********************************

.. Why we use Multipass + command to install it
.. include:: ../includes/pro-fix-intro.txt

In this tutorial, we will introduce the ``pro fix`` command and guide
you to a simple example of using it to solve a CVE/USN.

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

.. # The basic case is shared between Howto and Tutorial
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

As mentioned at the beginning, there might be more scenarios that you may
encounter using ``pro fix`` as well as options to control what exactly will
happen, those are covered in detail in:

* :ref:`How to Understand scenarios encountered using pro fix to solve a CVE/USN <pro-fix-howto>`
* :ref:`How to know what the fix command would change? <pro-fix-dry-run>`
* :ref:`How to skip fixing related USNs <pro-fix-skip-related>`

.. Instructions for how to connect with us
.. include:: ../includes/contact.txt

.. LINKS

.. include:: ../links.txt

.. _CVE-2020-15180: https://ubuntu.com/security/CVE-2020-15180
.. _CVE-2020-25686: https://ubuntu.com/security/CVE-2020-25686
