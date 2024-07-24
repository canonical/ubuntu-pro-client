What data does Canonical collect from Ubuntu Pro machines?
**********************************************************

For the purposes of delivering Ubuntu Pro services to customers in compliance
with the terms of the Ubuntu Pro subscription, some system data is sent to
Canonical servers. This data is sent via a couple different methods, depending
on the service and the purpose of that particular data element.

This document categorizes data collection by method of collection.

APT Package Downloads
=====================

If you have any of the following services enabled, then the following data
collection method will be in use whenever downloading packages for one of
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

Whenever you ``apt install`` a package from a pro service (or ``apt upgrade``
to a version of a package from a pro service), ``apt`` will make a GET request
to ``esm.ubuntu.com`` that includes the package name and version and HTTP
basic auth credentials that are tied to the Ubuntu Pro Subscription.

For example, installing the ``hello`` package from ``esm-apps`` will result in
a request that looks something like this:

.. code-block:: text
   https://bearer:$resource_token@esm.ubuntu.com/apps/ubuntu/pool/main/h/hello/hello_2.10-2ubuntu4+esm1_amd64.deb

This request is necessary to download the Pro update and it necessarily
includes the following data.

- ubuntu codename (e.g. "jammy")
- package name (e.g. "hello")
- package version (e.g. "2.10-2ubuntu4+esm1")
- package architecture (e.g. "amd64")

Because this request is necessarily authenticated and the authentication token
is tied to a particular Ubuntu Pro subscription, this data is inherently tied
to the Ubuntu Pro subscription that authenticated access to the package.

Livepatch Downloads
===================

If you have ``livepatch`` enabled, then the following data is sent in order to
download the correct kernel patches:

- kernel version (e.g. "6.8.0-38.38-generic")
- machine architecture (e.g. "amd64")

Because this request is necessarily authenticated and the authentication token
is tied to a particular Ubuntu Pro subscription, this data is inherently tied
to the Ubuntu Pro subscription that authenticated access to the package.


Machine Activity Checks
=======================

Regardless of which services you have enabled, if a machine is attached to an
Ubuntu Pro subscription, the following data is collected and updated regularly.

- distribution (e.g. "Ubuntu")
- release codename (e.g. "noble")
- kernel version (e.g. "6.8.0-38.38-generic")
- machine architecture (e.g. "amd64")
- is the machine a desktop (e.g. "true")
- virtualization type (e.g. "docker")
- services enabled (e.g. "ros" and "realtime-kernel generic variant")
- time the machine was attached (e.g. "2024-07-24T13:54:07+00:00")
- version of ``ubuntu-pro-client`` (e.g. "33.2~24.04")

These data elements are collected to ensure machines that are attached to a
particular Ubuntu Pro contract are compliant with the terms of that particular
contract.
