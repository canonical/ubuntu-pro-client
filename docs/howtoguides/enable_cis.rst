.. _manage-cis:

How to enable CIS or USG
************************

On Ubuntu 20.04 LTS (Focal) and later releases, CIS was
`replaced by USG <usg_>`_. If you are running Focal (or a later release) and
want to enable ``usg``, then select the **USG** tab below.

.. Make sure Pro is up to date
.. include:: ./enable-disable/update-pro.txt

.. Reminder to attach sub and check service status
.. include:: ./enable-disable/check-status.txt

Enable the service
==================

To access the tooling, first enable the software repository as follows:

.. tab-set::
    
    .. tab-item:: CIS
       :sync: CIS

        .. code-block:: bash

            $ sudo pro enable cis

    .. tab-item:: USG
       :sync: USG

        .. code-block:: bash

            $ sudo pro enable usg 

You should see output like the following, indicating that the package has been
installed:

.. tab-set::
    
    .. tab-item:: CIS
       :sync: CIS

        .. code-block:: text

            Updating CIS Audit package lists
            Updating standard Ubuntu package lists
            Installing CIS Audit packages
            CIS Audit enabled
            Visit https://ubuntu.com/security/cis to learn how to use CIS

    .. tab-item:: USG
       :sync: USG

        .. code-block:: text

            Updating Ubuntu Security Guide package lists
            Ubuntu Security Guide enabled
            Visit https://ubuntu.com/security/certifications/docs/usg for the next steps


Once the feature is enabled you can `follow the documentation`_
for both the CIS and USG tooling, to run the provided hardening audit scripts.

Disable the service
===================

If you wish to disable the service, you can use the following command: 

.. tab-set::
    
    .. tab-item:: CIS
       :sync: CIS

        .. code-block:: bash

            $ sudo pro disable cis

    .. tab-item:: USG
       :sync: USG

       .. code-block:: bash

            $ sudo pro disable usg 

You can verify that the service has been correctly disabled by once again
running the ``pro status`` command.

Note that this command will only remove the APT sources, but not uninstall any
of the packages installed with the service.

To purge the service, removing all APT packages installed with it, see
:ref:`how to disable and purge services <disable_and_purge>`. This does not
remove any of your configuration, it only removes the packages.

.. LINKS

.. include:: ../links.txt

.. _follow the documentation: https://ubuntu.com/security/certifications/docs/usg/cis
