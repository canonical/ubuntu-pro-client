.. _pro-fix-dry-run:

How to know what the ``fix`` command would change?
**************************************************

As outlined in our explanation of the different scenarios encountered when
:ref:`using pro fix to solve a CVE/USN <pro-fix-howto>`,
``pro fix`` can encounter many conditions
and running it might or might not lead to upgrades of packages on your system.

If you are unsure and want to check what changes will happen to your system when you run
``pro fix`` to address a CVE/USN, you can simulate a run using the
``--dry-run`` flag to see which packages will be installed on the system. For
example, this is the output of running ``pro fix USN-5079-2 --dry-run``:

.. code-block:: text

    WARNING: The option --dry-run is being used.
    No packages will be installed when running this command.
    USN-5079-2: curl vulnerabilities
    Associated CVEs:
    https://ubuntu.com/security/CVE-2021-22946
    https://ubuntu.com/security/CVE-2021-22947
    1 affected source package is installed: curl
    (1/1) curl:
    A fix is available in Ubuntu Pro: ESM Infra.
    The machine is not attached to an Ubuntu Pro subscription.
    To proceed with the fix, a prompt would ask for a valid Ubuntu Pro token.
    { pro attach TOKEN }
    Ubuntu Pro service: esm-infra is not enabled.
    To proceed with the fix, a prompt would ask permission to automatically enable
    this service.
    { pro enable esm-infra }
    { apt update && apt install --only-upgrade -y curl libcurl3-gnutls }
    ✔ USN-5079-2 is resolved.

You can see that using ``--dry-run`` will also indicate which actions would
need to happen to completely address the USN/CVE. Here we can see that the
package fix can only be accessed through the ``esm-infra`` service. Therefore,
we need an Ubuntu Pro subscription, as can be seen in this part of the output:

.. code-block:: text

    The machine is not attached to an Ubuntu Pro subscription.
    To proceed with the fix, a prompt would ask for a valid Ubuntu Pro token.
    { pro attach TOKEN }

Additionally, it informs you that even with a subscription, we need the
specific ``esm-infra`` service to be enabled:

.. code-block:: text

    Ubuntu Pro service: esm-infra is not enabled.
    To proceed with the fix, a prompt would ask permission to automatically enable
    this service.
    { pro enable esm-infra }

.. note::

    After performing these steps during a ``fix`` command without
    ``--dry-run``, your machine should no longer be affected by the USN we
    used as an example.
