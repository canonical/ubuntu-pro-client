.. _manage-esm:

How to manage Expanded Security Maintenance (ESM) services
**********************************************************

For Ubuntu LTS releases, ESM for Infrastructure (``esm-infra``) and ESM for
Applications (``esm-apps``) are automatically enabled after you attach the
Ubuntu Pro Client subscription to your account. However, if you chose to
disable them initially, you can enable them at any time from the command line
using the Ubuntu Pro Client (``pro``).

.. Make sure Pro is up to date
.. include:: ./enable-disable/update-pro.txt

.. Reminder to attach sub and check service status
.. include:: ./enable-disable/check-status.txt

Enable ``esm-apps`` and ``esm-infra``
=====================================

If either of the ``esm-apps`` or ``esm-infra`` services are disabled and you
want to enable them, run the following command to enable ESM-Infra:

.. code-block:: bash

    sudo pro enable esm-infra

Or the following for ESM-Apps:

.. code-block:: bash

    sudo pro enable esm-apps

Update your packages
====================

When you enable the ESM-Infra and/or ESM-Apps repositories, especially on
Ubuntu 14.04 and 16.04, you may see a number of package updates available that
were not available previously.

Even if your system indicated that it was up to date before enabling
``esm-infra`` or ``esm-apps``, make sure to check for new package updates after
you enable them:

.. code-block:: bash

    sudo apt upgrade

If you have cron jobs set to install updates, or other unattended upgrades
configured, be aware that this will likely result in a number of packages being
updated with the ``esm-infra`` and ``esm-apps`` content.

Running ``apt upgrade`` will apply all available package updates, including
the ones in ``esm-infra`` and ``esm-apps``.

Disable the services
====================

If you wish to disable the services, you can use the following command to
disable ESM-Infra:

.. code-block:: bash

    sudo pro disable esm-infra

Or the following command to disable ESM-Apps:

.. code-block:: bash

    sudo pro disable esm-apps

Note that this command will only remove the APT sources, but not uninstall the
packages installed with the services.

To purge the services, removing the APT packages installed with them, see
:ref:`how to disable and purge services <disable_and_purge>`.

Notes
=====

- For more information about ESM-Apps and ESM-Infra, see
  :ref:`our explanatory guide <expl-ESM>`.

.. LINKS

.. include:: ../links.txt
