What data is collected from active Ubuntu Pro machines?
*******************************************************

If a machine is attached to an Ubuntu Pro subscription, the following data is
collected and updated regularly (default: every 6 hours).

- Distribution (e.g. "Ubuntu")
- Release codename (e.g. "Noble")
- Kernel version (e.g. "6.8.0-38.38-generic")
- Machine architecture (e.g. "amd64")
- Is the machine a desktop? (e.g. "true")
- Virtualisation type (e.g. "Docker")
- Services enabled (e.g. "ros" and "realtime-kernel generic variant")
- When the machine was attached (e.g. "2024-07-24T13:54:07+00:00")
- Version of ``ubuntu-pro-client`` (e.g. "33.2~24.04")

These data elements are collected to ensure machines that are attached to a
particular Ubuntu Pro contract are compliant with the terms of that particular
contract.

Data sent to provide service
============================

The following data is not purposefully collected, but is sent to Canonical
servers in order to provide Ubuntu Pro services.

APT package downloads
---------------------

If you have any of the following services enabled, then the data collection
method described below will be in use whenever downloading packages for one of
these services.

- ``anbox-cloud``
- ``cc-eal``
- ``cis``
- ``esm-apps``
- ``esm-infra``
- ``fips``
- ``fips-preview``
- ``fips-updates``
- ``realtime-kernel``
- ``ros``
- ``ros-updates``
- ``usg``

Whenever you ``apt install`` a package from a Pro service (or ``apt upgrade``
to a version of a package from a Pro service), ``apt`` will make a GET request
to ``esm.ubuntu.com`` that includes the package name and version, and HTTP
basic authentication credentials that are tied to the Ubuntu Pro subscription.

For example, installing the ``hello`` package from ``esm-apps`` will result in
a request that looks something like this:

.. code-block:: text

   https://bearer:$resource_token@esm.ubuntu.com/apps/ubuntu/pool/main/h/hello/hello_2.10-2ubuntu4+esm1_amd64.deb

This request is necessary to download the Pro update and includes the
following data.

- Ubuntu codename (e.g. "Jammy")
- Package name (e.g. "hello")
- Package version (e.g. "2.10-2ubuntu4+esm1")
- Package architecture (e.g. "amd64")

Because this request needs to be authenticated and the authentication token is
tied to a particular Ubuntu Pro subscription, this data is inherently tied to
the Ubuntu Pro subscription that authenticated access to the package.

Livepatch downloads
-------------------

If you have ``livepatch`` enabled, then the following data is sent in order to
download the correct kernel patches:

- Kernel version (e.g. "6.8.0-38.38-generic")
- Machine architecture (e.g. "amd64")

Similarly to APT package downloads, because this request needs to be
authenticated and the authentication token is tied to a particular Ubuntu Pro
subscription, this data is inherently tied to the Ubuntu Pro subscription that
authenticated access to the package.
