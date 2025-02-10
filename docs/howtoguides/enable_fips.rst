.. _manage-fips:

How to manage FIPS
******************

.. note::

    Check `the FIPS documentation`_ to verify which Ubuntu releases have FIPS
    available.

.. caution::

    **Disabling FIPS is not recommended**: only enable FIPS on machines
    intended expressly to be used for FIPS.

To use FIPS, one can either launch existing Ubuntu premium support images which
already have the FIPS kernel and security pre-enabled on first boot at
`AWS Ubuntu Pro FIPS images <fips_AWS_>`_,
`Azure Pro FIPS images <fips_Azure_>`_, and GCP Pro FIPS images.

Alternatively, you can enable FIPS using the Ubuntu Pro Client, which will
install a FIPS-certified kernel and core security-related packages such as
``openssh-server/client`` and ``libssl``. 

To enable FIPS, run:

.. code-block:: bash

    $ sudo pro enable fips-updates

You should see output like the following, indicating that the FIPS packages
have been installed:

.. code-block:: text

    Installing FIPS Updates packages
    FIPS Updates enabled
    A reboot is required to complete install.

Enabling FIPS should be performed during a system maintenance window since
this operation makes changes to underlying SSL-related libraries and requires
a reboot into the FIPS-certified kernel.

.. note::

    ``fips-updates`` is the recommended way of enabling FIPS, as it will bring
    the FIPS-compliant packages with security updates and coverage. There is
    also a ``fips`` service, which has only the certified packages, *without
    further security updates*, but that is deprecated from Ubuntu 22.04 (Jammy
    Jellyfish) onward.

.. caution::
    
    Once you enable FIPS, enabling some Pro services may not be possible. For
    a complete view of which services are incompatible with FIPS, refer to the
    :doc:`services compatibility matrix <../references/compatibility_matrix>`


How to disable FIPS
===================

If you wish to disable FIPS, you can use the following command:

.. code-block:: bash

    sudo pro disable fips-updates

Note that this command will only remove the APT sources, but not uninstall the
packages installed with the service. Your system will **still have the FIPS
packages installed** after FIPS is disabled.

To purge the service, removing the APT packages installed with it, potentially
removing also the FIPS kernel, see
:ref:`how to disable and purge services <disable_and_purge>`.


.. LINKS

.. include:: ../links.txt

.. _the FIPS documentation: https://ubuntu.com/security/certifications/docs/fips
