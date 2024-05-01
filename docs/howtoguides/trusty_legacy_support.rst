How to enable esm-infra-legacy on Trusty
*****************************************

The ``esm-infra-legacy`` service can be enabled with the Legacy Support add-on to grant an additional two years of 
extended security coverage. This service is only available on 14.04 LTS (Trusty), since the release has reached
the end of its support period for ``esm-infra``. Check out this article to `learn more about the expansion of Long Term Support for Trusty <https://canonical.com/blog/canonical-expands-long-term-support-to-12-years-starting-with-ubuntu-14-04-lts>`_ and how to contact Canonical to purchase this additional support.


Make sure ``ua`` is up-to-date
===============================

All Trusty systems come with ``ua`` pre-installed through the
``ubuntu-advantage-tools`` package. To make sure that you're running the latest
version of ``ua``, run the following commands:

.. code-block:: bash

    sudo apt update && sudo apt install ubuntu-advantage-tools

Note that on Trusty, Ubuntu Pro is referred to by its previous name: "Ubuntu Advantage" (or ``ua``).


Check the status of the services
================================

After you have attached to a Pro subscription and
updated the ``ubuntu-advantage-tools`` package, you can check which services
are enabled by running the following command:

.. code-block:: bash

    sudo ua status

This will show you which services are enabled or disabled on your machine,
(output truncated for brevity). With the addition of Legacy Support, it will
now show the esm-infra-legacy service on Trusty:

.. code-block:: text

    SERVICE          ENTITLED  STATUS    DESCRIPTION
    esm-infra        yes       enabled   Expanded Security Maintenance for Infrastructure
    esm-infra-legacy yes       disabled  Expanded Security Maintenance for Infrastructure on Legacy Instances
    livepatch        yes       enabled   Canonical Livepatch service

.. _enable_legacy:

Enabling esm-infra-legacy
==========================

If you are entitled to the ``esm-infra-legacy`` service as shown above, you can enable it by running:

.. code-block:: bash

    sudo ua enable esm-infra-legacy


What if ``esm-infra-legacy`` is not entitled?
===================================================

If ``ua status`` shows that you are not entitled to the service, you
will first need to buy access to the service, as mentioned at the top of this page.

Once you have purchased a support subscription, run the following command
on your machine to refresh the contract definitions:

.. code-block:: bash

    sudo ua refresh


After refreshing the contract data, you can confirm that the service is now entitled by running:


.. code-block:: bash

    sudo ua status

The output should now show that you are entitled to the ``esm-infra-legacy`` service, and you can now enable the service as outlined :ref:`in the enablement section <enable_legacy>`.


Trusty caveats
===============

There are some known caveats for the Trusty version of `ubuntu-advantage-tools`:

Disabling ``esm-infra`` also disables ``esm-infra-legacy``
----------------------------------------------------------

If you disable ``esm-infra``, this will (due to internal dependencies) also disable
``esm-infra-legacy``. Although updates will **only** be applied via ``esm-infra-legacy``,
we recommend keeping both services enabled. This is not true in reverse: if you want
to disable ``esm-infra-legacy``, doing so will not disable ``esm-infra``.
``do-release-upgrade`` fails if packages are installed from ``esm-infra``
-------------------------------------------------------------------------

If ``esm-infra`` is enabled **and** packages are installed from that source, the
``do-release-upgrade`` operation will fail since there will be an APT dependency issue
when performing the operation.

You can address this issue by running ``do-release-upgrade`` with the following command:

.. code-block:: bash

    sudo RELEASE_UPGRADER_ALLOW_THIRD_PARTY=1 do-release-upgrade
  
It is important to note that you will need to re-enable the Ubuntu Pro services again
once you have upgraded to Xenial, since Trusty lacks the correct mechanisms to re-enable
the Pro services automatically after a ``do-release-upgrade``.

Note that this is only the case when upgrading from Trusty to Xenial. The Ubuntu Pro
Client is fully supported from Xenial onwards, where these issues have already been fixed.


Why 14.04 (Trusty) no longer receives new Ubuntu Pro Client features
---------------------------------------------------------------------

For a further reduced risk of regressions on 14.04 (Trusty) the Pro client package is almost frozen.
Hence it is not receiving regular upstream backports like newer Ubuntu LTS releases do. Beyond
version 19.7 there won't be updates except any critical CVE maintenance or features explicitly
targeted for Trusty like ``esm-infra-support`` in 2024.

Version 19.7 has full-featured support of the applicable Ubuntu Pro
service offerings ``esm-infra``, ``esm-infra-legacy`` and ``livepatch``.
