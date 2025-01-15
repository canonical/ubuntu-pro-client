.. _attach_multiple_machines:

Attach multiple machines
========================

When attaching machines to a Pro subscription, you have several options. For a single machine, refer to :ref:`How to attach <attach>` for CLI instructions or :ref:`How to attach using a config file <attach-with-config>` for configuration file steps.

For deploying Pro across multiple machines, Cloud-init provides the most efficient solution. This guide demonstrates how to use Cloud-init to distribute your Pro token and configure Pro services across multiple machines at once.

Configure using Cloud-init
--------------------------

The next step is to use cloud-init to configure your machines with the pro token.

To do this, a cloud-init configuratioin file is required. Here, we will first create a file with the name "cloud-init.yaml" and add the pro token to it by copying the following code block to the file:

.. code-block:: yaml

    #cloud-config
    ubuntu_pro:
        token: <YOUR_PRO_TOKEN>


Replace <YOUR_PRO_TOKEN> with the pro token you received from the Ubuntu Pro Dashboard. For more information on how to obtain a pro token, see `Ubuntu Pro <Pro_>`_.

For more information on how to configure Pro with cloud-init, take a look at the guide here: `Configure Pro in cloud-init <CLOUD_INIT_PRO_>`_.

Cloud-init also has comprehensive guides on configuring cloud-init for different platforms:

    - `QEMU`_
    - `LXD`_
    - `Ansible`_

Verifying deployment
--------------------

After deployment, execute these commands on the host to confirm Pro subscription is attached:

.. code-block:: bash

   $ sudo pro status

You should see the following (output truncated):

.. code-block:: text

    SERVICE          ENTITLED  STATUS    DESCRIPTION
    esm-apps         yes       enabled   Expanded Security Maintenance for Applications
    esm-infra        yes       enabled   Expanded Security Maintenance for Infrastructure
    fips             yes       disabled  NIST-certified core packages
    fips-updates     yes       disabled  NIST-certified core packages with priority security updates
    livepatch        yes       enabled   Canonical Livepatch service

Here, the columns "ENTITLED" and "STATUS" indicate whether the service is entitled to the subscription and whether it is enabled or disabled. For more information on understanding the output of the status command,  refer to :ref:`this explanation <pro-status-output>`.

.. LINKS

.. include:: ../links.txt

.. _CLOUD_INIT_PRO:  https://cloudinit.readthedocs.io/en/latest/reference/modules.html#ubuntu-pro
.. _QEMU: https://cloudinit.readthedocs.io/en/latest/tutorial/qemu.html
.. _LXD: https://cloudinit.readthedocs.io/en/latest/tutorial/lxd.html
.. _Ansible: https://cloudinit.readthedocs.io/en/latest/reference/yaml_examples/ansible_managed.html
