.. _how-to:

How-to guides
*************

If you have a specific goal and are already familiar with the Ubuntu Pro Client
(``pro``), our how-to guides have more in-depth detail than our tutorials and
can be applied to a wider range of situations.

They will help you to achieve a particular end result, but may require you to
understand and adapt the steps to fit your specific requirements.

The Pro Client comes pre-installed on every Ubuntu release. To access your
Ubuntu Pro services, you first need to attach your machine to your subscription.

Attaching machines
==================

.. include:: howtoguides/attach_index.rst
   :start-line: 4
   :end-before: .. TOC

.. toctree::
   :maxdepth: 2
   :hidden:
   
   Attach... <howtoguides/attach_index>

Enabling services
=================

.. include:: howtoguides/enable_index.rst
   :start-line: 4
   :end-before: .. TOC

.. toctree::
   :maxdepth: 2
   :hidden:
      
   Enable... <howtoguides/enable_index>

Handling vulnerabilities
========================

.. include:: howtoguides/fix_index.rst
   :start-line: 4
   :end-before: .. TOC
   
.. toctree::
   :maxdepth: 2
   :hidden:

   Handle vulnerabilities... <howtoguides/fix_index>

Configuring messages
====================

.. include:: howtoguides/configure_index.rst
   :start-line: 4
   :end-before: .. TOC

.. toctree::
   :maxdepth: 2
   :hidden:

   Configure messages... <howtoguides/configure_index>

Setting up proxies
==================

The Ubuntu Pro Client supports proxy setups. These guides will help you to
configure your proxies correctly.

.. toctree::
   :maxdepth: 1

   Configure a proxy <howtoguides/configure_proxies>
   Configure TLS-in-TLS proxy <howtoguides/configure_tls_in_tls_proxy>

Using Pro Client with Docker
============================

There are several Ubuntu Pro services that may be useful in a Docker image.

.. toctree::
   :maxdepth: 1

   Enable Ubuntu Pro services in a Dockerfile <howtoguides/enable_in_dockerfile>
   Create an Ubuntu FIPS Docker image <howtoguides/create_a_fips_docker_image.rst>

Ubuntu Pro Client for Clouds
============================

Ubuntu Pro is supported by AWS, Azure and GCP. For more details about this
support, see :ref:`our explanation <expl-about-pro-cpc>`. These how-to guides
will direct you in setting up your Public Cloud environment.

.. toctree::
   :maxdepth: 1

   Create a customized Cloud Ubuntu Pro image <howtoguides/create_pro_golden_image>
   Cloud Ubuntu Pro images with FIPS updates <howtoguides/create_a_fips_updates_pro_cloud_image>

Ubuntu Pro Client LXD integration
=================================

.. toctree::
   :maxdepth: 1

   How to set up the Ubuntu Pro LXD integration <howtoguides/use_pro_lxd_guests>

Troubleshooting
===============

You may occasionally need to check the version of the Pro Client, collect logs
in order to report a bug, or release a corrupted lock on a file.

.. toctree::
   :maxdepth: 1

   Check Pro Client version <howtoguides/check_pro_version>
   Collect data logs for bug reporting <howtoguides/how_to_collect_logs>
   Get rid of corrupted locks <howtoguides/get_rid_of_corrupt_lock>
