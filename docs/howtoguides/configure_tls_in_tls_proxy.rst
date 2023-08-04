How to configure a TLS-in-TLS proxy
***********************************

.. note:: Support for TLS-in-TLS proxying was added in version 28.1 of the Ubuntu Pro Client.

.. warning:: TLS-in-TLS is only supported by the Ubuntu Pro Client on Ubuntu 18.04 and later.

If you need to set ``https_proxy`` to a proxy that uses ``https://`` (a practice commonly referred to as "TLS-in-TLS"), you need to follow a few extra steps to ensure all Ubuntu Pro actions work correctly.


Install the pycurl dependency
===============================

For TLS-in-TLS proxying, ``pro`` switches to using ``pycurl`` -- but ``pycurl`` may not be installed by default on your machine. To install it, run:

.. code:: bash

   sudo apt install python3-pycurl

.. note::
   If you don't do this and try to set the TLS-in-TLS proxy anyway, you will get an error that looks like this:

   .. code:: none

      To use an HTTPS proxy for HTTPS connections, please install pycurl with `apt install python3-pycurl`

Ensure the proxy's HTTPS certificate will be trusted by Livepatch
=================================================================

.. tip:: You can skip this step if you don't plan on using Livepatch.

Livepatch requires configuration separate from the rest of the Ubuntu system for trusting certificates. Even if your proxy's certificate is signed by a well known certificate authority (CA), it may not be trusted by Livepatch by default.

To ensure Livepatch will trust your proxy's certificate, first pre-install the livepatch-client:

.. code:: bash

   sudo snap install canonical-livepatch

Then download the certificate of your proxy (or of the CA) in `PEM`_ format and configure livepatch-client to trust it:

.. code:: bash

   sudo canonical-livepatch config ca-certs=@stdin < /path/to/certificate.pem

Verify the PEM contents are present and accurate under the ``ca-certs`` field by running:

.. code:: bash

   sudo canonical-livepatch config

Set the HTTPS proxy via the ``pro config`` command
==================================================

Now that everything else is set up, you can configure the Ubuntu Pro Client to use the TLS-in-TLS proxy:

.. code:: bash

   sudo pro config https_proxy=https://your.proxy.here:1234


Success!
========

Now with the TLS-in-TLS proxy configured, you can :ref:`configure any other proxies you need <configure_proxies>` and then use your Ubuntu Pro token to :ref:`attach your machine <get_token_and_attach>`.

.. LINKS:
.. _PEM: https://en.wikipedia.org/wiki/Privacy-Enhanced_Mail
