.. _expl-ESM:

About ESM, esm-apps and esm-infra
*********************************

Expanded Security Maintenance (ESM)
===================================

In the earlier version of Ubuntu Pro, when security fixes were only guaranteed
for packages in the 'main' repository, ESM used to be known as *Extended
Security Maintenance*. At that time, it referred to the additional five years
of security coverage that Pro provided after the standard five years' of
security coverage expired. It *extended* the security coverage to ten years.
This has since become known as ``esm-infra`` (more on that below!).

Since then, Pro has grown considerably in the size and scope of what it
provides. Where we originally only guaranteed security maintenance for
packages in the 'main' repository, we have now *expanded* the scope of our
security fixes to also include packages in the 'universe' repository. So, when
Pro went into General Availability in early 2023 and became available to all,
ESM became *Expanded Security Maintenance* to reflect the expanded scope of
our coverage.

What are 'main' and 'universe'?
===============================

There are tens of thousands of Ubuntu packages, all organised into sets in
*repositories*.

'*Main*' is the set of packages we identified as our focus when we launched
Ubuntu - they are packages that are either installed on every machine, or very
widely used for all kinds of deployments, from desktop to cloud. When we
launched Ubuntu LTS, we made a commitment to security-support these packages
and their dependencies in 'main' for five years, free of charge. There were
initially about 1,000 packages in 'main', and today that number has grown to
about 2,300 per Ubuntu release.

The '*universe*' repository holds all of the other open source packages in
Ubuntu; from Debian and the Ubuntu community. 'Universe' is a much bigger
repository, with over 23,000 packages per release. Historically those packages
came with no security maintenance commitment from Canonical. Nevertheless,
Canonical and the Ubuntu community provided best-effort maintenance for those
packages. With the launch of Ubuntu Pro, all of the packages of Ubuntu
'universe' get the same security maintenance commitment from Canonical as
packages in Ubuntu 'main'.

What are ESM-infra and ESM-apps?
================================

There are two streams of broad-based security updates for packages; we label
these 'apps' (for applications) and 'infra' (for infrastructure).

The ``esm-apps`` stream covers all 'universe' packages for ten years from the
release of the LTS. 

The ``esm-infra`` stream covers 'main' packages for the period after the
standard five year security maintenance of 'main' packages ends. We call this
'infra' because it is commonly used to build our private cloud, storage and
Kubernetes clusters, where 'universe' packages are not typically deployed. 

Commercial and enterprise customers can get a lower-cost Ubuntu Pro
(infra-only) subscription only the 'infra' components are needed, which equates
to our original ESM offering.

How can I enable ``esm-infra`` and ``esm-apps``?
================================================

You can manage ``esm-infra`` and ``esm-apps`` using ``pro`` on the command
line. To find out how, read our guide on
:ref:`enabling and disabling these services <manage-esm>` on your machine.

Are ``esm-infra`` and ``esm-apps`` packages preferred over regular updates?
===========================================================================

Yes. The Pro Client will deliver the following configuration files to ``apt``
to ensure the ``esm`` updates are preferred when running ``apt upgrade``:

- ``/etc/apt/preferences.d/ubuntu-pro-esm-infra``
- ``/etc/apt/preferences.d/ubuntu-pro-esm-apps``

These files are *pinning* the packages coming from ``esm`` to give them a higher
priority than the standard priority defined in APT. This means that the version to be
installed by ``apt`` (in ``apt install`` or ``apt upgrade``) or by unattended-upgrades will
always be the highest ``esm`` version available for a given package, even if a
higher version is theoretically available from a non-esm source.

This behaviour guarantees that if you have ``esm-infra`` or ``esm-apps`` enabled,
your system will always have the ``esm`` patches installed for any package
available in the ESM repositories.

Although the preference files listed above will always be delivered by the
package, they will only take effect when the referenced sources are available, i.e. when the services are enabled. Otherwise, it
is safe to keep those files around.

check the `APT configuration article`_ in the Debian wiki to learn more about
pinning and priorities.

Why do we set this preference for the ESM packages ?
====================================================

Once you enable the ESM services you have immediate access to the security
updates provided by Canonical for your Ubuntu system. Setting the preference
guarantees that no automatically installed updates will ever revert a
previously applied security patch, unless some manual operation overrides the
default behaviour set by the Pro Client.

How does this preference affect PPAs ?
======================================

If you have any third party PPAs configured on your system, then the ESM
repositories will be preferred over these as well. That means if a
particular package has two different versions (one coming from the
PPA and the other from ESM) the ESM version will be chosen, even if the
PPA version is higher.

If you don't want this behaviour, and you want the the PPA version to be
automatically installed instead, you need to set at least the same preference
value used for ESM (510) for the PPA. To do that, please check the
`APT configuration article`_ in the Debian wiki to learn more about
pinning and priorities.

.. LINKS

.. _APT configuration article: https://wiki.debian.org/AptConfiguration#apt_preferences_.28APT_pinning.29
