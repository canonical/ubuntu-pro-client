.. _attach-with-config:

How to attach with a configuration file
***************************************

To attach with a configuration file, you must run ``pro attach`` with the
``--attach-config`` flag, passing the path of the configuration file you intend
to use.

When using ``--attach-config`` the token must be passed in the file rather than
on the command line. This is useful in situations where it is preferred to keep
the secret token in a file.

Optionally, the attached config file can be used to override the services that
are automatically enabled as a part of the attach process.


Get an Ubuntu Pro token
=======================

Retrieve your Ubuntu Pro token from the `Ubuntu Pro portal <Pro_>`_. Log in
with your "Single Sign On" credentials, the same credentials you use for
https://login.ubuntu.com.

After you have logged in you can go to the
`Ubuntu Pro Dashboard <Pro_dashboard_>`_ associated with your user account. It
will show you all subscriptions currently available to you and for each
associated token.

Note that even without buying anything you can always obtain a free personal
token that way, which provides you with access to several of the Ubuntu Pro
services.


The attach config file
======================

An attach config file looks like this:

.. code-block:: yaml

    token: YOUR_TOKEN_HERE  # required
    enable_services:        # optional list of service names to auto-enable
      - esm-infra
      - esm-apps
      - cis

And can be passed via the CLI with the following command:

.. code-block:: bash

    sudo pro attach --attach-config /path/to/file.yaml
