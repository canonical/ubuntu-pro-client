.. _manage-cc:

How to manage CC EAL
********************

`Common Criteria <CC_>`_ is supported only on Ubuntu 16.04 (Xenial) and 18.04
(Bionic). This means that CC EAL2 can be enabled on both Xenial and Bionic LTS
releases, but the installed scripts that configure CC EAL2 on those machines
will only run on Xenial 16.04.4 and Bionic 18.04.4 point releases.

.. Make sure Pro is up to date
.. include:: ./enable-disable/update-pro.txt

.. Reminder to attach sub and check service status
.. include:: ./enable-disable/check-status.txt

Enable and auto-install
=======================

To enable CC EAL2 using the Ubuntu Pro Client, run the following command:

.. code-block:: bash

    $ sudo pro enable cc-eal

You should see output like this: 

.. code-block:: text

    Updating package lists
    (This will download more than 500MB of packages, so may take some time.)
    Installing CC EAL2 packages
    CC EAL2 enabled
    Please follow instructions in /usr/share/doc/ubuntu-commoncriteria/README to configure EAL2

This indicates that the CC EAL2 package has been successfully installed.

Enable and manually install
===========================

.. hint::

    The ``--access-only`` flag was introduced in Pro Client version 27.11.

If you would like to enable access to the CC EAL2 ``apt`` repository but not
install the packages immediately, use the ``--access-only`` flag while
enabling:

.. code-block:: bash

    $ sudo pro enable cc-eal --access-only

With that extra flag you'll see output like the following:

.. code-block:: text

    One moment, checking your subscription first
    Updating package lists
    Skipping installing packages: ubuntu-commoncriteria
    CC EAL2 access enabled

To install the packages at a later time, you can then run:

.. code-block:: bash

    $ sudo apt install ubuntu-commoncriteria

Disable the service
===================

If you wish to disable ``cc-eal``, you can use the following command:

.. code-block:: bash

    sudo pro disable cc-eal

Note that this command will only remove the APT source, but not uninstall any
of the packages installed with the service.

To purge the service, removing the APT packages installed with it, see
:ref:`how to disable and purge services <disable_and_purge>`. This will not
remove any configuration, but will remove the packages.

.. LINKS

.. include:: ../links.txt
