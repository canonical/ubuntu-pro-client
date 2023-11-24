.. _manage-realtime:

How to manage real-time kernel
******************************

Pre-requisites
==============

The `real-time kernel <realtime_>`_ is currently only supported on Ubuntu
22.04 LTS (Jammy). For more information, feel free to
`contact our real-time team`_.

Enable and auto-install
=======================

.. important:: 

    Once you enable real-time kernel, enabling some Pro services will not be
    possible. For a complete view of which services are compatible with
    real-time kernel, refer to the
    :doc:`services compatibility matrix <../references/compatibility_matrix>`.

To ``enable`` the real-time kernel through the Ubuntu Pro Client, please run:

.. code-block:: bash

    $ sudo pro enable realtime-kernel

You'll need to acknowledge a warning, and then you should see output like the
following, indicating that the real-time kernel package has been installed.

.. code-block:: text

    One moment, checking your subscription first
    The Real-time kernel is a beta version of the 22.04 Ubuntu kernel with the
    PREEMPT_RT patchset integrated for x86_64 and ARM64.

    This will change your kernel. You will need to manually configure grub to
    revert back to your original kernel after enabling real-time.

    Do you want to continue? [ default = Yes ]: (Y/n) yes
    Updating package lists
    Installing Real-time kernel packages
    Real-time kernel enabled
    A reboot is required to complete install.

After rebooting you'll be running the real-time kernel!

Enable and manually install
===========================

.. important::

    The ``--access-only`` flag was introduced in Pro Client version 27.11

If you would like to enable access to the real-time kernel APT repository but
not install the kernel right away, use the ``--access-only`` flag when you
enable it, as follows:

.. code-block:: bash

    $ sudo pro enable realtime-kernel --access-only

With this extra flag you'll see output like this:

.. code-block:: text

    One moment, checking your subscription first
    Updating package lists
    Skipping installing packages: ubuntu-realtime
    Real-time kernel access enabled

To install the kernel you can then run:

.. code-block:: bash

    $ sudo apt install ubuntu-realtime

You'll need to reboot after installing to boot into the real-time kernel.

Notes
=====

* Real-time kernel is not compatible with Livepatch. If you wish to use the
  real-time kernel but Livepatch is enabled, ``pro`` will warn you and offer
  to disable Livepatch first.

.. LINKS

.. include:: ../links.txt

.. _contact our real-time team: https://ubuntu.com/kernel/real-time/contact-us
