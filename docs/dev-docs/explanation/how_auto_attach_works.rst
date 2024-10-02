.. _how_auto_attach_works:

How auto-attach works
*********************

The ``pro auto-attach`` command follows a specific flow on every Public Cloud
Ubuntu Pro image:

1. Identify which cloud the command is running on by running the ``cloud-id``
   command provided by the `cloud-init`_ package. Currently, we only support
   AWS, Azure and GCP when running the command. The command will fail if run on
   other cloud types.

2. Fetch the cloud metadata. This metadata is a cryptographically-signed JSON
   blob that provides the necessary information for the contract server to
   validate the machine and return a valid Pro token. To fetch that metadata,
   every cloud provides a different endpoint:

   * **AWS**: ``http://169.254.169.254/latest/dynamic/instance-identity/pkcs7``
   * **Azure**: ``http://169.254.169.254/metadata/attested/document?api-version=2020-09-01``
   * **GCP**: ``http://metadata/computeMetadata/v1/instance/service-accounts/default/identity``

.. note::
   On AWS, the client will also try the IPv6 address (``[fd00:ec2::254]``) to
   fetch the metadata if the IPv4 address doesn't work.

3. Send this metadata JSON blob to the contract server at:

   ``https://contracts.canonical.com/v1/clouds/CLOUD-TYPE/token``

   Where ``CLOUD-TYPE`` is the cloud name we identified in step 1.

   The contract server will verify if the metadata is signed correctly based on
   the cloud. Additional checks are performed to see if the metadata is valid.
   For example, the contract server checks if the product ID provided in the
   metadata is a valid product. If any problems are found in the metadata, the
   contract server will produce an error response.

4. After the contract server validates the metadata, it returns a token that is
   used to attach the machine to a Pro subscription. To attach the machine, we
   will reach the following contract server endpoint:

   ``https://contracts.canonical.com/v1/context/machines/token``

   We will pass the token provided in step 3 as the header bearer token for
   this request.

5. The contract returns a JSON specification based on the provided token. This
   JSON contains all the directives the Pro Client needs to set up the machine
   and enable the services associated with the token.

6. Disable the ``ubuntu-advantage.service`` :ref:`daemon <systemd_units>`, if
   it is running. If the machine is detached, this daemon will be started again.

You can disable the ``pro auto-attach`` command by adding the following lines
to your ``uaclient.conf`` configuration file, which is located by default
located at ``/etc/ubuntu-advantage/uaclient.conf``:

.. code-block:: bash

    features:
      disable_auto_attach: true

.. LINKS
.. _cloud-init: https://docs.cloud-init.io/en/latest/
