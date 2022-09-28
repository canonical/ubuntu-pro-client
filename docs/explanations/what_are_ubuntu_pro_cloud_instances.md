# What is a Public Cloud Ubuntu Pro machine?

Ubuntu Pro images are published to [AWS](https://ubuntu.com/aws/pro), [Azure](https://ubuntu.com/azure/pro) and [GCP](https://ubuntu.com/gcp/pro) which come with Ubuntu
Pro support and services built in. On first boot, Ubuntu Pro images will automatically attach
to an Ubuntu Pro support contract and enable necessary Ubuntu Pro services so
that no extra setup is required to ensure a secure and supported Ubuntu machine.

There are two primary flavors of Ubuntu Pro images in clouds:

* Ubuntu Pro: Ubuntu LTS images with attached Ubuntu Pro support with kernel Livepatch and
ESM security access already enabled. Ubuntu Pro images are entitled to enable any additional Ubuntu Pro
services (like [`fips`](../howtoguides/enable_fips.md) or [`usg`](../howtoguides/enable_cis.md)).
* Ubuntu Pro FIPS: Specialized Ubuntu Pro images for 16.04, 18.04 and 20.04 which come pre-enabled
with the cloud-optimized FIPS-certified kernel and all additional SSL and security hardening
enabled. These images are available as [AWS Ubuntu Pro FIPS](https://ubuntu.com/aws/fips), [Azure Ubuntu Pro FIPS](https://ubuntu.com/azure/fips) and GCP Ubuntu Pro FIPS.
