.. _roll_out_multiple_machines:

How to roll out your pro token across multiple machines
=======================================================

This guide will show you how to roll out your pro token across multiple machines using cloud-init for configuration.

Configure using Cloud-init
--------------------------

The next step is to usea cloud-init to configure your machines with the pro token.

To do this, a cloud-init configuratioin file is required. Create a cloud-init.yaml file with the following content:

.. code-block:: yaml

    #cloud-config
    ubuntu_pro:
        token: <YOUR_PRO_TOKEN>


Replace <YOUR_PRO_TOKEN> with the pro token you received from the Ubuntu Pro Dashboard.

For more information on how to configure the pro token with cloud-init, take a look at the guide here: `Configure Pro in cloud-init <CLOUD_INIT_PRO_>`_.

Cloud-init also has comprehensive guides on configuring cloud-init for different platforms:

    - `QEMU`_
    - `LXD`_
    - `Ansible`_

Verifying deployment
--------------------

After deployment, execute these commands on the host to confirm Pro subscription is attached:

.. code-block:: bash

   $ sudo pro status

.. LINKS

.. include:: ../links.txt

.. _CLOUD_INIT_PRO:  https://cloudinit.readthedocs.io/en/latest/reference/modules.html#ubuntu-pro
.. _QEMU: https://cloudinit.readthedocs.io/en/latest/tutorial/qemu.html
.. _LXD: https://cloudinit.readthedocs.io/en/latest/tutorial/lxd.html
.. _Ansible: https://cloudinit.readthedocs.io/en/latest/reference/yaml_examples/ansible_managed.html
