.. _manage-realtime:

How to manage Real-time Ubuntu
******************************

`Real-time Ubuntu <realtime_>`_ is supported on Ubuntu 22.04 LTS (Jammy)
and later releases. To find out more about the supported Ubuntu versions and
what kernel variants are available, refer to 
`the supported releases page <kernel_variant_>`_.

Attach your subscription
========================

If you have not yet attached your machine to an Ubuntu Pro subscription, you
will need to do so in order to enable Real-time Ubuntu. You can do so by
running the following command:

.. code-block:: bash

    sudo pro attach

And follow the instructions in your terminal window. For a more complete guide
to the attach process, refer to our
:ref:`how to attach <get_token_and_attach>` guide.

.. Make sure Pro is up to date
.. include:: ./enable-disable/update-pro.txt

.. important:: 

    Once you enable Real-time Ubuntu, enabling some Pro services will not be
    possible. To see which services are compatible with the
    real-time kernel, refer to the
    :doc:`services compatibility matrix <../references/compatibility_matrix>`.
    
    If you try to enable Real-time Ubuntu while an incompatible service is
    already enabled, the Pro Client will inform you and offer to disable that
    service.

Enable and install automatically
================================

The Real-time Ubuntu kernel package is installed using the APT package manager
when you enable ``realtime-kernel`` through the Pro Client.

If you want to access the repository but not install the package immediately,
skip to `Install and enable manually`_.

Otherwise, `select the correct kernel variant <kernel_variant_>`_ for your OS
and processor, and use the corresponding command below:

.. tab-set::

   .. tab-item:: Generic

      .. code-block:: shell

         sudo pro enable realtime-kernel
      
      .. caution::
         The generic Real-time kernel is not intended for Raspberry Pi.
         Using the Pro Client to install it on these platforms will make your
         system unusable.

   .. tab-item:: Raspberry Pi

      For Raspberry Pi 4 and 5:

      .. code-block:: shell

         sudo pro enable realtime-kernel --variant=raspi

   .. tab-item:: Intel IOTG

      For 12th Gen Intel® Core™ processors:

      .. code-block:: shell

         sudo pro enable realtime-kernel --variant=intel-iotg

You will need to acknowledge a warning, then you will see a confirmation
message like the following that the Real-time Ubuntu package has been
installed:

.. code-block:: text

   One moment, checking your subscription first
   Real-time kernel cannot be enabled with Livepatch.
   Disable Livepatch and proceed to enable Real-time kernel? (y/N) y
   Disabling incompatible service: Livepatch
   The Real-time kernel is an Ubuntu kernel with PREEMPT_RT patches integrated.

   This will change your kernel. To revert to your original kernel, you will need
   to make the change manually.

   Do you want to continue? [ default = Yes ]: (Y/n) Y
   Updating Real-time kernel package lists
   Updating standard Ubuntu package lists
   Installing Real-time kernel packages
   Real-time kernel enabled
   A reboot is required to complete install.

You will now need to reboot your machine to complete the process. After
rebooting, you will be running Real-time Ubuntu.

Install and enable manually
===========================

To access the Real-time Ubuntu repository but not install the package
immediately, you can use the ``--access-only`` flag, which was introduced in
Pro Client version 27.11:

.. code-block:: shell-session

   $ sudo pro enable realtime-kernel --access-only

   One moment, checking your subscription first
   Real-time kernel cannot be enabled with Livepatch.
   Disable Livepatch and proceed to enable Real-time kernel? (y/N) y
   Disabling incompatible service: Livepatch
   Updating Real-time kernel package lists
   Skipping installing packages: ubuntu-realtime
   Real-time kernel access enabled


Now that Real-time Ubuntu is accessible, you can install and enable it whenever
you wish. For example, to install the generic Real-time kernel (not suitable
for Raspberry Pi):

.. code-block:: shell

   sudo apt install ubuntu-realtime

After rebooting, you'll be running Real-time Ubuntu.

Next steps
==========

For more information about Real-time Ubuntu and how it can help you, refer
to the `official Real-time Ubuntu`_ documentation.

.. LINKS

.. include:: ../links.txt

.. _kernel_variant: https://canonical-real-time-ubuntu-documentation.readthedocs-hosted.com/en/latest/reference/releases/
.. _official Real-time Ubuntu: https://canonical-real-time-ubuntu-documentation.readthedocs-hosted.com/en/latest/
