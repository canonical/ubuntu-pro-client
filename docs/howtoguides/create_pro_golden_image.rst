.. _create_pro_golden_image:

How to create a customised Cloud Ubuntu Pro image
*************************************************

* Launch an Ubuntu Pro instance on your cloud of choice
* Customise the instance as you see fit
* Run the command: ``sudo truncate -s 0 /etc/machine-id``
* Use your cloud platform to clone or snapshot this VM as a **golden image**

For more detailed instructions on creating customised Cloud Ubuntu Pro images, refer to the following guides:

* `AWS guide <custom_image_AWS_>`_ 
* `Azure guide <custom_image_Azure_>`_
* `GCP guide <custom_image_GCP_>`_

.. tip::

    Prior to Pro Client version 27.11, when launching instances based on this
    instance, you will need to re-enable any non-standard Ubuntu Pro services
    that you enabled on the image. This will be faster on the new instance
    because it was already enabled on the image. You will not need to reboot
    for e.g. ``fips`` or ``fips-updates``.

.. LINKS

.. include:: ../links.txt