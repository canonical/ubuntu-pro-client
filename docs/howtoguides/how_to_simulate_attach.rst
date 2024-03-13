How to simulate the ``attach`` operation
****************************************

If you are unsure what the state of your machine will be after running
``attach`` with a specific token, you can simulate running the ``attach``
operation by running:

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
