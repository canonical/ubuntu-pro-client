.. _simulate-attach:

How to simulate the ``attach`` operation
****************************************

If you are unsure what the state of your machine will be after running
``attach`` with a specific token, you can simulate running the ``attach``
operation.

Get an Ubuntu Pro token
=======================

You first need to retrieve the Ubuntu Pro token you want to test from the
`Ubuntu Pro portal <Pro_>`_. Log in with your "Single Sign On" credentials,
the same credentials you use for https://login.ubuntu.com.

After you have logged in you can go to the
`Ubuntu Pro Dashboard <Pro_dashboard_>`_ associated with your user account. It
will show you all subscriptions currently available to you and for each
associated token.

Note that even without buying anything you can always obtain a free personal
token that way, which provides you with access to several of the Ubuntu Pro
services.

Simulate the attach process
===========================

Once you have your token, you can run the following command (replacing
`YOUR_TOKEN` with the token you retrieved from the dashboard):

.. code-block:: bash

    $ pro status --simulate-with-token YOUR_TOKEN

After running the command, you should see a modified status table, similar to
this one:

.. code-block:: text

    SERVICE          AVAILABLE  ENTITLED   AUTO_ENABLED  DESCRIPTION
    cc-eal           yes        yes        no            Common Criteria EAL2 Provisioning Packages
    cis              yes        yes        no            Security compliance and audit tools
    esm-infra        yes        yes        yes           Expanded Security Maintenance for Infrastructure
    fips             yes        yes        no            NIST-certified core packages
    fips-updates     yes        yes        no            NIST-certified core packages with priority security updates
    livepatch        yes        yes        yes           Canonical Livepatch service

Here, you can see which services that token is entitled to, while also
verifying which services will be enabled by default through the
**AUTO_ENABLED** column. The services marked as "yes" here will be
automatically enabled when running an ``attach`` operation.

.. note::

    If you want more information about the **AVAILABLE** and **ENTITLED**
    columns, please refer to :ref:`this explanation <pro-status-output>`.

If there are services that will be auto-enabled that you don't want to enable,
or you only want to enable specific services, you may want to run ``attach``
:ref:`using a config file <attach-with-config>` instead of the usual attach
process. Otherwise, you can run:

.. code-block:: bash

    $ sudo pro attach --no-auto-enable

This will prevent the auto-enabling of any services while attaching a
particular machine.

.. LINKS

.. include:: ../links.txt
