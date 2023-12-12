.. _manage-anbox:

How to manage Anbox Cloud
*************************

To use Anbox, you will need to enable it directly through the Ubuntu Pro
Client (``pro``), which will install all the necessary snaps and set up the APT
sources needed for the service.

.. note::

    `Anbox Cloud <anbox_>`_ is supported on 20.04 and 22.04 releases.

.. Make sure Pro is up to date
.. include:: ./enable-disable/update-pro.txt

.. Reminder to attach sub and check service status
.. include:: ./enable-disable/check-status.txt

Enable Anbox
============

To enable Anbox Cloud, run:

.. code-block:: bash

    $ sudo pro enable anbox-cloud

.. important:: 

    The Anbox Cloud service can only be installed on **containers** using the
    ``--access-only`` flag. This option will only set up the APT sources for
    Anbox, but not install any of the snaps.

You should see output like the following, indicating that Anbox Cloud
was correctly enabled on your system:

.. code-block:: text

    One moment, checking your subscription first
    Installing required snaps
    Installing required snap: amc
    Installing required snap: anbox-cloud-appliance
    Installing required snap: lxd
    Updating package lists
    Anbox Cloud enabled
    To finish setting up the Anbox Cloud Appliance, run:

    $ sudo anbox-cloud-appliance init

    You can accept the default answers if you do not have any specific
    configuration changes.
    For more information, see https://anbox-cloud.io/docs/tut/installing-appliance

You have probably noticed that the output states an **additional step** is
required to complete the Anbox Cloud setup. Let us run the required command:

.. code-block:: bash

    $ sudo anbox-cloud-appliance init

You can now confirm that the service is enabled by running the ``pro status``
command again. It should contain the following line for ``anbox-cloud``:

.. code-block:: text

    SERVICE          ENTITLED  STATUS    DESCRIPTION
    anbox-cloud      yes       enabled   Scalable Android in the cloud   

Disable the service
===================

If you wish to disable Anbox, you can use the following command to
disable it:

.. code-block:: bash

    sudo pro disable anbox-cloud

Note that this command will only remove the APT sources, but will not uninstall
the snaps.

To also purge the service, removing all the APT packages installed with it, see
:ref:`how to disable and purge services <disable_and_purge>`.

.. LINKS

.. include:: ../links.txt
