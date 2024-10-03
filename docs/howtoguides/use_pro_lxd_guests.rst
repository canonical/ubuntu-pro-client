How to get Ubuntu Pro on LXD guests
***********************************

Pro client v35 allows LXD guests to get Ubuntu Pro during boot. For the integration to
work properly you need to:

1) Have LXD installed from the `6/stable` channel
2) Have the host machine attached to Ubuntu Pro

Once that is done, you can control the LXD integration
with the `lxd_guest_attach` conffiguration. This configuration has three possible values:

* **off**: This turns off the LXD integration with Ubuntu Pro. This is also the `default` value for
  this feature
* **available**: This value will allow LXD guests to attach to Pro, but it won't perform that action
  automatically. You will need to run the `pro auto-attach` command in the guest for it to attach to
  a Ubuntu Pro license
* **on**: This value will make the LXD guest to attach to Pro automatically during the boot stage

To set any of those values, you can use the following command:

.. code-block:: bash

    $ pro config set lxd_guest_attach=(off|available|on)

