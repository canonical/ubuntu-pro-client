What is the Pro daemon?
*******************************

Ubuntu Pro Client sets up a daemon for two types of machines:

* Azure and GCP generic cloud images
* Cloud Pro images

For the first type of images, the daemon is responsible
for detecting if an Ubuntu Pro license has been purchased for the machine.
If a Pro license is detected, then the machine is automatically attached.

For the Pro cloud images, the daemon is responsible for retrying the auto-attach
operation if it fails on first boot. When that happens, users will be notified in
MOTD or when they run `pro status` with a message like:

.. code-block:: text

   Failed to automatically attach to an Ubuntu Pro subscription 1 time
   The failure was due to: ERROR_MSG
   The next attempt is scheduled for RETRY_DATE
   You can try manually with `sudo pro auto-attach`.

The "retry auto-attach" operation will keep retrying for a **month**. If at the end, we cannot attach
to the machine, we display the following message to the user:

.. code-block:: text

   Failed to automatically attach to an Ubuntu Pro subscription NUM times.
   The most recent failure was due to: ERROR_MSG
   Try re-launching the instance or report this issue by running `ubuntu-bug ubutu-advantage-tools`
   You can try manually with `sudo pro auto-attach`.

Disabling the daemon
---------------------

If you are not interested in Ubuntu Pro services and don't want your machine to
be automatically attached to your subscription, you can safely stop and disable
the daemon using ``systemctl`` as follows:

.. code-block:: bash

    sudo systemctl stop ubuntu-advantage.service
    sudo systemctl disable ubuntu-advantage.service
