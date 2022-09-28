# How to create a customized Cloud Ubuntu Pro image

* Launch a Ubuntu Pro instance on your cloud of choice
* Customize the instance as you see fit
* `sudo rm /etc/machine-id`
* Use your cloud platform to clone or snapshot this VM as a golden image

> **Note**
> Prior to version 27.11 - when launching instances based on this instance, you will need to re-enable any non-standard Ubuntu Pro services that you enabled on the image. This will be faster on the new instance because it was already enabled on the image. You will not need to reboot for e.g. `fips` or `fips-updates`.
