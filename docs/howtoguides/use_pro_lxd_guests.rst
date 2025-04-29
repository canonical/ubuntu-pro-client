How to get Ubuntu Pro on LXD guests
***********************************

Pro client v35 allows LXD guests to get Ubuntu Pro during boot. For the integration to
work properly you need to:

* Have a version of LXD which supports the feature installed in your system:

  * version 5.21.4 or later (if running from ``5/stable``)
  * version 6.3 or later (if running from ``6/stable``)
  * the ``latest/stable`` version (recommended)

* Have the host machine attached to Ubuntu Pro, running the Client version
  ``35.1`` or later

Once that is done, you can control the LXD integration
with the `lxd_guest_attach` configuration. This configuration has three possible values:

* **off**: This turns off the LXD integration with Ubuntu Pro. This is also the `default` value for
  this feature
* **available**: This value will allow LXD guests to attach to Pro, but it won't perform that action
  automatically. You will need to run the `pro auto-attach` command in the guest for it to attach to
  the Ubuntu Pro license
* **on**: This value will attach the LXD guest to Pro automatically during the boot stage

To set any of those values, you can use the following command:

.. code-block:: bash

    $ pro config set lxd_guest_attach=(off|available|on)

