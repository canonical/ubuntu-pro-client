# About Public Cloud Ubuntu Pro images

Ubuntu Pro images are published to [AWS](https://ubuntu.com/aws/pro),
[Azure](https://ubuntu.com/azure/pro) and [GCP](https://ubuntu.com/gcp/pro). 
All of these come with Ubuntu Pro support and services built in.

On first boot, Ubuntu Pro images will automatically attach to an Ubuntu Pro
support contract and enable all necessary Ubuntu Pro services so that no extra
setup is required to ensure a secure and supported Ubuntu machine.

There are two primary flavors of Ubuntu Pro images in clouds: *Ubuntu Pro*, and
*Ubuntu Pro FIPS*.

## Ubuntu Pro

These Ubuntu LTS images are provided already attached to Ubuntu Pro support,
with kernel Livepatch and ESM security access enabled. Ubuntu Pro images are
entitled to enable any additional Ubuntu Pro services (like
[`fips`](../howtoguides/enable_fips.md) or
[`usg`](../howtoguides/enable_cis.md)).

## Ubuntu Pro FIPS

These specialized Ubuntu Pro images for 16.04, 18.04 and 20.04 come pre-enabled
with the cloud-optimized FIPS-certified kernel, as well as all additional SSL
and security hardening enabled. These images are available as
[AWS Ubuntu Pro FIPS](https://ubuntu.com/aws/fips),
[Azure Ubuntu Pro FIPS](https://ubuntu.com/azure/fips) and GCP Ubuntu Pro FIPS.
