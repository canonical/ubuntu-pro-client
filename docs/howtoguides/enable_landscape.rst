How to enable Landscape
***********************

You can register a machine with Landscape via the ``pro enable landscape``
command. You can register interactively for convenience, or non-interactively
which is useful for hands-off automation.

To register a machine, you'll need, at minimum, your Landscape Account Name
and a name for the machine you are registering. If you're not using Landscape
SaaS (https://landscape.canonical.com), then you'll also need the URL of your
hosted Landscape server.

Enable interactively
====================

To register your machine by interactively providing your Landscape account
details at the CLI, run:

.. code:: bash

   sudo pro enable landscape

This command will install ``landscape-client`` and start up an interactive
wizard to complete the Landscape registration for the machine.

Enable non-interactively
========================

If you know the details of your Landscape setup then you can register a
machine without using the wizard. Under the hood, `pro` installs and executes
``landscape-config``, so you can pass any `parameters supported by`_
``landscape-config`` to ``pro enable landscape`` after a ``--``. You should
also use the ``--assume-yes`` flag to automatically accept the defaults for
any un-provided parameters.

The command to enable Landscape takes the following format:

.. code:: bash

   sudo pro enable landscape <pro enable parameters> -- <landscape-config parameters>

Which, when the parameters are added, should look something like this:

.. code:: bash

   sudo pro enable landscape --assume-yes -- --account-name <my-account> --computer-title <my-computer>

That command will install ``landscape-client`` and pass the provided parameters
after ``--`` to the ``landscape-config`` tool to automatically register the
machine.

What next?
==========

After successfully running ``pro enable landscape``, either interactively
or non-interactively, an administrator of your Landscape account will need to go
to the "Pending Computers" page in Landscape to accept the machine you just
registered.

And that's it! The machine should now appear in the Landscape dashboard for
management.

.. LINKS:
.. _parameters supported by: https://manpages.ubuntu.com/landscape-config
