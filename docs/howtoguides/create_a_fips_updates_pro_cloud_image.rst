.. _create_a_fips_updates_pro_cloud_image:

How to customise a cloud Ubuntu Pro image with FIPS updates
***********************************************************

Launch an Ubuntu Pro instance on your cloud
===========================================

See the following links for up to date information about Pro for each supported
cloud:

* `AWS <pro_AWS_>`_
* `Azure <pro_Azure_>`_
* `GCP <pro_GCP_>`_

Enable FIPS updates
===================

Wait for the standard Ubuntu Pro services to be set up:

.. code-block:: bash

    sudo pro status --wait

Use the enable command to set up FIPS updates:

.. code-block:: bash

    sudo pro enable fips-updates --assume-yes

Now, reboot the instance:

.. code-block:: bash

    sudo reboot

And verify that ``fips-updates`` is enabled in the output of ``pro status``:

.. code-block:: bash

    sudo pro status

Also remove the ``machine-id`` so that it is regenerated for each instance
launched from the snapshot.

.. code-block:: bash

    sudo rm /etc/machine-id

Snapshot the instance as a Cloud image
======================================

Cloud-specific instructions are here:

* `AWS`_
* `Azure`_
* `GCP`_

Launch your custom image
========================

Use your specific cloud to launch a new instance from the custom image.

.. note::

    For versions of the Ubuntu Pro Client prior to 27.11, you will need to
    re-enable ``fips-updates`` on each instance launched from the custom image.

    This won't require a reboot and is only necessary to ensure the instance
    gets updates to FIPS packages when they become available.

    .. code-block:: bash

        sudo pro enable fips-updates --assume-yes
    
    This can be scripted using `cloud-init user data`_ at launch time:
    
    .. code-block:: yaml
    
        #cloud-config
        # Enable fips-updates after pro auto-attach and reboot after cloud-init completes
        runcmd:
          - 'pro status --wait'
          - 'pro enable fips-updates --assume-yes'
    
.. LINKS

.. include:: ../links.txt

.. _AWS: https://docs.aws.amazon.com/toolkit-for-visual-studio/latest/user-guide/tkv-create-ami-from-instance.html
.. _Azure: https://learn.microsoft.com/en-us/azure/virtual-machines/capture-image-resource
.. _GCP: https://cloud.google.com/compute/docs/machine-images/create-machine-images

.. _cloud-init user data: https://cloudinit.readthedocs.io/en/latest/reference/modules.html#runcmd
