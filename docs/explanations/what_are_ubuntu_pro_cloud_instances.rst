.. _expl-about-pro-cpc:

About Public Cloud Ubuntu Pro images
************************************

Ubuntu Pro images are published to `AWS <pro_AWS_>`_, `Azure <pro_Azure_>`_
and `GCP <pro_GCP_>`_. All of these come with Ubuntu Pro support and services
built in.

On first boot, Ubuntu Pro images will automatically attach to an Ubuntu Pro
support contract and enable all necessary Ubuntu Pro services so that no extra
setup is required to ensure a secure and supported Ubuntu machine.

There are two primary flavors of Ubuntu Pro images in clouds: **Ubuntu Pro**,
and **Ubuntu Pro FIPS**.

Ubuntu Pro
==========

These Ubuntu LTS images are provided already attached to Ubuntu Pro support,
with kernel Livepatch and ESM security access enabled. Ubuntu Pro images are
entitled to enable any additional Ubuntu Pro services (like
:ref:`FIPS <manage-fips>` or :ref:`USG <manage-cis>`).

Ubuntu Pro FIPS
===============

These specialised Ubuntu Pro images for 16.04, 18.04 and 20.04 come pre-enabled
with the cloud-optimised FIPS-certified kernel, as well as all additional SSL
and security hardening enabled. These images are available as
`AWS Ubuntu Pro FIPS <fips_AWS_>`_,
`Azure Ubuntu Pro FIPS <fips_Azure_>`_ and `GCP Ubuntu Pro FIPS <fips_GCP_>`_.

.. _what-is-auto-attach:

The ``ubuntu-pro-auto-attach`` package
======================================

The ``ubuntu-pro-auto-attach`` package is used by
:ref:`Public Cloud Ubuntu Pro <expl-about-pro-cpc>` machines to automate the
process of attaching a machine on boot. This package ships a ``systemd`` unit
that runs an auto-attach command on first boot.

.. LINKS

.. include:: ../links.txt
