.. _use_staging_environment:

Use the contracts staging environment
*************************************

You can change the contract server that the Pro Client will use by setting the
following option in your ``uaclient.conf`` configuration file, (by default
located at ``/etc/ubuntu-advantage/uaclient.conf``).

.. code-block:: yaml

   contract_url: https://contracts.staging.canonical.com

.. note:
   You might be using a local ``uaclient.conf`` file when running the Pro
   Client. In that case, you should change your local file instead.
