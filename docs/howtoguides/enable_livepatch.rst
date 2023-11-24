.. _manage-livepatch:

How to manage Livepatch
***********************

For Ubuntu LTS releases, `Livepatch`_ is automatically enabled after you attach
your Ubuntu Pro subscription. However, you can choose to disable it initially
via the dashboard, and then enable it at a later time from the command line
using the Ubuntu Pro Client (``pro``). 

.. Make sure Pro is up to date
.. include:: ./enable-disable/update-pro.txt

.. Reminder to attach sub and check service status
.. include:: ./enable-disable/check-status.txt

How to enable Livepatch
=======================

.. important::

    Once you enable Livepatch, enabling some Pro services will not be possible
    until Livepatch is disabled again. For a complete view of which services
    are compatible with Livepatch, refer to the
    :doc:`services compatibility matrix <../references/compatibility_matrix>`.

If Livepatch is disabled and you want to enable it, run the following command:

.. code-block:: bash

    $ sudo pro enable livepatch

You should see output like the following, indicating that the Livepatch snap
package has been installed successfully:

.. code-block:: text

    One moment, checking your subscription first
    Installing snapd
    Updating package lists
    Installing canonical-livepatch snap
    Canonical livepatch enabled.

Check Livepatch status after installation
=========================================

If you're interested in the detailed status of the Livepatch client once it has
been installed, use the following command:

.. code-block:: bash

    $ sudo canonical-livepatch status

Unsupported kernels
-------------------

Although you can enable Livepatch on an unsupported kernel, since patches are
kernel-specific, you will not receive any updates from Livepatch if your kernel
is not supported. 

The ``pro status`` command will warn you in its output if Livepatch is not
supported:

.. code-block:: text

    SERVICE          ENTITLED  STATUS    DESCRIPTION
    esm-apps         yes       enabled   Expanded Security Maintenance for Applications
    esm-infra        yes       enabled   Expanded Security Maintenance for Infrastructure
    livepatch        yes       warning   Current kernel is not supported
    realtime-kernel  yes       disabled  Ubuntu kernel with PREEMPT_RT patches integrated

    NOTICES
    The current kernel (5.19.0-46-generic, amd64) is not supported by livepatch.
    Supported kernels are listed here: https://ubuntu.com/security/livepatch/docs/kernels
    Either switch to a supported kernel or `pro disable livepatch` to dismiss this warning.

The ``canonical-livepatch status`` command will also warn you if your kernel is
unsupported (output truncated for brevity):

.. code-block:: bash

    ...
    server check-in: succeeded
    kernel state: ✗ kernel not supported by Canonical 
    patch state: ✓ no livepatches needed for this kernel yet
    ...

You can also check
`the kernel support matrix <supported_kernels_>`_
to see if your kernel is supported by Livepatch. To find out more, refer to
this explanation of `how Livepatch works`_.

How to disable Livepatch
========================

Enabling Livepatch installs the Livepatch client as a snap package, and there
are a few possible ways to disable it. The simplest is to use the Pro Client:

.. code-block:: bash

    sudo pro disable livepatch

If you also want to remove the Livepatch client from your machine, you can
then use the following command:

.. code-block:: bash

    snap remove canonical-livepatch

For other options, you can also refer to `the Livepatch documentation`_.

Notes
=====

- For more information about the Livepatch client and how to use it, refer to
  the `official Livepatch client documentation`_.

- Livepatch is not compatible with FIPS-certified kernels or with the
  `real-time kernel <realtime_>`_, and should not be enabled if you wish to
  use those services. If Livepatch is enabled and you try to enable an
  incompatible service, ``pro`` will notify you and offer to disable Livepatch
  first.

.. LINKS

.. include:: ../links.txt

.. _how Livepatch works: https://ubuntu.com/security/livepatch/docs/livepatch/explanation/howitworks
.. _the Livepatch documentation: https://ubuntu.com/security/livepatch/docs/livepatch/how-to/disable
.. _official Livepatch client documentation: https://ubuntu.com/security/livepatch/docs
