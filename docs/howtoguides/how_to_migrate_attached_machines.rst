.. _how-to-migrate-attached-machines:

How to manage Ubuntu Pro attachment when moving machines
********************************************************

This guide explains what happens to your Ubuntu Pro attachment when you move,
clone, rebuild, or delete a machine, and what actions (if any) you need to
take in each case.

Ubuntu Pro attachment information is stored locally on the machine. The
subscription's active machine count is based on activity. If a machine is
stopped or deleted, it will eventually be removed from the active count
automatically. No manual detach is required.

.. note::

   Run ``sudo pro status`` or ``sudo pro refresh`` at any time to verify the
   current attachment state of a machine.

Moving a VM to another host or hypervisor
-----------------------------------------

When you move an attached VM to a different host, hypervisor, or virtual
environment (for example, a live migration or export/import), the Pro
attachment travels with it. The attachment data is part of the filesystem,
so no re-attachment is needed after the move.

#. Move the VM using your platform's standard tooling.
#. After the move, verify the attachment is intact:

   .. code-block:: bash

      sudo pro status

No further action is required. The machine continues to be counted as one
active machine on your subscription, as it was before.

Cloning an attached VM
-----------------------

When you clone an attached VM, the clone inherits the attachment from the
original. Both the original and the clone will be counted as separate active
machines on your subscription.

If you intend to **replace** the original with the clone (for example, for
testing or migration), stop or delete the original. It will eventually be
removed from the active count automatically.

.. note::

   If you are creating a **reusable template or golden image** from an attached
   VM, you should not leave the image in an attached state. See
   :ref:`create_pro_golden_image` for the recommended approach to creating
   Ubuntu Pro golden images.

#. Clone the VM using your platform's standard tooling.
#. Verify the attachment on the new clone:

   .. code-block:: bash

      sudo pro status

#. If you no longer need the original, stop or delete it. No detach is needed
   before deletion.

Rebuilding a machine with a fresh Ubuntu installation
------------------------------------------------------

If you reinstall a fresh Ubuntu image, the new installation does not carry over the previous Pro attachment.
You will need to attach the rebuilt machine to your subscription:

.. code-block:: bash

   sudo pro attach <your-pro-token>

Your Pro token is available from the `Ubuntu Pro Dashboard <Pro_dashboard_>`_.

If the previous machine is no longer in use, there is no need to detach it
first. It will eventually be removed from the active count automatically.

Decommissioning or deleting a machine
--------------------------------------

You do not need to detach a machine before decommissioning or deleting it. Once
the machine is gone and no longer communicates with the Ubuntu Pro service, it
will eventually be removed from the active count automatically.

You can detach before deleting, but this is optional:

.. code-block:: bash

   sudo pro detach

Verifying the result
--------------------

After any migration operation, use the following commands to confirm the state
of your attachment:

- Check the current attachment status and enabled services:

  .. code-block:: bash

     sudo pro status

- Force a refresh to sync with the Ubuntu Pro service:

  .. code-block:: bash

     sudo pro refresh

.. LINKS

.. include:: ../links.txt
