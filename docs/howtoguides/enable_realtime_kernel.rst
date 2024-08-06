How to enable Real-time Ubuntu
==============================

Prerequisites
-------------

`Real-time Ubuntu`_ is supported on specific Ubuntu releases; see :doc:`../reference/releases`.


Attach an Ubuntu Pro token
--------------------------

Real-time Ubuntu is available through an `Ubuntu Pro`_ security and compliance
subscription. If you don't already have access to "Pro", it's free for personal
use.

.. important:: 

   Once you enable Real-time Ubuntu, it won't be possible to enable certain
   other Pro services. The external documentation for Pro Client describes which
   services are `compatible with Real-time Ubuntu`_.

   Real-time Ubuntu is not compatible with Livepatch. If Livepatch is enabled
   when you install Real-time Ubuntu, Pro will offer to disable it before
   continuing.

When running this command without a token, it will generate a short code
and prompt you to attach the machine to your Ubuntu Pro account using
a web browser:

.. code-block:: shell

   sudo pro attach

.. tip::
   Set ``-h``/ ``--help`` flag to see the user manual for this or any other Pro command.

Install and enable automatically
--------------------------------

The Real-time Ubuntu kernel is installed using the APT package manager. If you wish to
access the repository but not install the package immediately, skip to `Install
and enable manually`_.

Otherwise, install Real-time Ubuntu and automatically select the right version
for your OS and processor:

.. note::
   The different variants of the realtime kernel aren't available in every Ubuntu release.
   Refer to :doc:`../reference/releases` for details.

Choose Generic or a corresponding variant:

.. tabs::

   .. group-tab:: Generic

      .. code-block:: shell

         sudo pro enable realtime-kernel
      
      .. caution::
         The generic realtime kernel is not intended for Raspberry Pi.
         Using the Pro client to install it on these platforms will make the system unusable.

   .. group-tab:: Raspberry Pi
      For Raspberry Pi 4 and 5:

      .. code-block:: shell

         sudo pro enable realtime-kernel --variant=raspi

   .. group-tab:: Intel IOTG
      For 12th Gen Intel® Core™ processors:

      .. code-block:: shell

         sudo pro enable realtime-kernel --variant=intel-iotg

You'll need to acknowledge a warning, then you should see confirmation that the
Real-time Ubuntu package is installed:

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

After rebooting, you'll be running Real-time Ubuntu.

Install and enable manually
---------------------------

To access the Real-time Ubuntu repository but not install the package
immediately, first use the ``--access-only`` flag:

.. code-block:: shell-session

   $ sudo pro enable realtime-kernel --access-only

   One moment, checking your subscription first
   Real-time kernel cannot be enabled with Livepatch.
   Disable Livepatch and proceed to enable Real-time kernel? (y/N) y
   Disabling incompatible service: Livepatch
   Updating Real-time kernel package lists
   Skipping installing packages: ubuntu-realtime
   Real-time kernel access enabled

.. important::

   The ``--access-only`` flag was introduced in Pro Client version 27.11.

Now that Real-time Ubuntu is accessible, you can install and enable it whenever
you wish.

For example, to install the generic realtime kernel (not suitable for Raspberry Pi):

.. code-block:: shell

   sudo apt install ubuntu-realtime


After rebooting, you'll be running Real-time Ubuntu.


.. LINKS
.. _Real-time Ubuntu: https://ubuntu.com/real-time
.. _Ubuntu Pro: https://ubuntu.com/pro
.. _compatible with Real-time Ubuntu: https://canonical-ubuntu-pro-client.readthedocs-hosted.com/en/latest/references/compatibility_matrix/
