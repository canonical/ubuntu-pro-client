Ubuntu Pro Client
#################

`Ubuntu Pro`_ is a suite of security services provided by Canonical. Whether
you’re an enterprise customer deploying systems at scale or want security
patching for your personal Ubuntu LTS at home, the Ubuntu Pro Client (``pro``)
is the command-line tool that will help you manage the services you need.

The Ubuntu Pro Client comes pre-installed on every Ubuntu system. You can run
``pro help`` in your terminal window to see a list of the ``pro``
services and commands available, or get started
:doc:`with our hands-on tutorial<tutorials/basic_commands>` to try it out in
a virtual environment.

Which services are for me?
==========================

Ubuntu Pro is a broad subscription designed to meet many different needs. You
are unlikely to want to use all of these tools and services at the same time,
so you are free to select the precise stream of updates and versions you want
to apply on any given machine covered by your Pro subscription.

To help you navigate the services offered through Ubuntu Pro, click on the tab
that best describes your needs for our suggestions on which services might be
of interest to you. For example, Pro includes a set of package versions that
are compliant with FIPS regulations. You will only want these versions on
machines that *need* to meet FIPS requirements, so you can choose to enable
that stream specifically on those machines.

.. tab-set::

    .. tab-item:: Commercial

       * **Expanded Security Maintenance (ESM)**

         If you're using any Ubuntu LTS -- Desktop or Server -- in a commercial
         setting and you rely on 'Universe' packages, or if you're on an older
         LTS and don't want to upgrade yet, you can get additional security
         support through `Expanded Security Maintenance (ESM)`_. We recommend
         it for everyone using Pro, and it's enabled by default. It includes
         two services:

         * ``esm-infra`` provides security updates for packages in the Ubuntu
           'main' repository (packages from Ubuntu) for five additional years
           beyond the standard five years of security maintenance of 'main'
           packages.

         * ``esm-apps`` covers packages in the 'universe' repository (which
           are from Debian and the community) for ten years after the LTS
           release. 

         * Whether you need one or both of these depends on your subscription.
           If you're not sure which services best support the needs of your
           organisation, contact us for `a security assessment`_.

       * **Livepatch**

         Ubuntu `Livepatch`_ reduces costly unplanned maintenance by patching
         vulnerabilities while the system runs. It removes the need to
         immediately reboot after a kernel upgrade so that you can schedule
         downtime when it's convenient. This tooling is available through
         ``livepatch`` and is one of the services we enable by default.

         * Find out more about what Livepatch can do for your organisation in
           the `Livepatch documentation`_, or learn
           :doc:`how to enable it<howtoguides/enable_livepatch>` with ``pro``.

       Want more information?

    .. tab-item:: Security certification

       Ubuntu provides security `compliance, certifications, and hardening`_:

       * **FIPS 140-2**

         * `FIPS 140-2 Certified Modules`_ are available through ``fips``.

         * Compliant but non-certified patches are available through
           ``fips-updates``.

         * Find out more :doc:`about managing FIPS<howtoguides/enable_fips>`.

       * **Ubuntu Security Guide (USG)**

         * In the 20.04 LTS we introduced the `Ubuntu Security Guide`_, which
           provides security tooling through ``usg``. It bundles together
           multiple key components, such as CIS benchmarking and DISA-STIG.

         * Before USG, Center for Internet Security `(CIS) Benchmark`_ tooling
           was available as a separate service through ``cis``. This can be
           used up to (and including) 20.04 LTS, but on all later LTS releases
           this functionality is provided through ``usg``.

         * Find out :doc:`how to manage USG (and CIS)<howtoguides/enable_cis>`
           with the Pro Client.

       * **Common Criteria**

         * `Common Criteria EAL2 (CC EAL)`_ certification tooling is available
           through ``cc-eal``. The Ubuntu 18.04 LTS and 16.04 LTS have both
           been certified.

         * Find out :doc:`how to enable CC EAL<howtoguides/enable_cc>` on
           your LTS.

       Want more information?

    .. tab-item:: Personal user

       * **Expanded Security Maintenance (ESM)**

         If you're using Pro on an LTS machine (Desktop or Server) you can get
         additional security support through
         `Expanded Security Maintenance (ESM)`_. We recommend it for everyone
         using Pro, and it's enabled by default. It includes two services:

         * ``esm-infra`` provides security updates for packages in the Ubuntu
           'main' repository (packages from Ubuntu) for five additional years
           beyond the standard five years of security maintenance of 'main'
           packages.

         * ``esm-apps`` covers packages in the 'universe' repository (which
           are from Debian and the community) for ten years after the LTS
           release. 

         * Read more
           :doc:`about ESM-Apps and ESM-Infra<explanations/about_esm>`.

       * **Livepatch**

         Ubuntu `Livepatch`_ removes the need to immediately reboot your
         machine after a patch is applied to the kernel, so you can perform
         device reboots when it's convenient for you. Although it's
         lightweight, it may not be suitable on a very small system with
         limited memory. Check our `list of supported kernels`_ if you're
         unsure.

         * Find out
           :doc:`how to enable Livepatch<howtoguides/enable_livepatch>`.

       Want more information?

    .. tab-item:: Specialty services

       * **ROS ESM**

         Our Robot Operating System Expanded Security Maintenance (`ROS ESM`_)
         service provides security maintenance for ROS LTS releases, starting
         with ROS Kinetic on Ubuntu 16.04 -- including packages from the Ubuntu
         'universe' repository.

         * ``ros`` provides security updates to the 600+ packages for ROS 1
           Kinetic and Melodic, and ROS 2 Foxy. 

         * ``ros-updates`` also gives you access to non-security updates.

         * Want to know how to enable ROS ESM? Check out
           `this introductory guide`_ by the ROS team to get started.

       * **Real-time kernel**

         The Ubuntu 22.04 LTS brought the new, enterprise-grade
         `real-time kernel`_, which reduces kernel latencies and ensures
         predictable performance for time-sensitive task execution. It was
         designed to deliver stable, ultra-low latency and security for
         critical telco infrastructure, but has applications across a wide
         variety of industries.

         * Find out `more information about real-time Ubuntu`_ and what it can
           do for your organisation. 

         * Or see our guide on
           :doc:`how to enable the real-time kernel<howtoguides/enable_realtime_kernel>`. 

       Want more information?

Explore our documentation
=========================

.. grid:: 1 1 2 2
   :gutter: 3

   .. grid-item-card:: **Tutorials**
       :link: tutorials
       :link-type: doc

       Get started - a hands-on introduction to Ubuntu Pro Client for new users

   .. grid-item-card:: **How-to guides**
       :link: howtoguides
       :link-type: doc

       Step-by-step guides covering key operations and common tasks

   .. grid-item-card:: **Explanation**
       :link: explanations
       :link-type: doc

       Discussion and clarification of key topics

   .. grid-item-card:: **Reference**
       :link: references
       :link-type: doc

       Technical information - specifications, APIs, architecture

-----

Getting help
============

Ubuntu Pro is a new product, and we're keen to know about your experience of
using it!

- **Have questions?**
  You might find the answers `in our FAQ`_.

- **Having trouble?**
  We would like to help! To get help on a specific page in this documentation,
  simply click on the "Give feedback" link at the top of that page. This
  will open up an issue in GitHub where you can tell us more about the problem
  you're having or suggestion you'd like to make, and we will do our best to
  resolve it for you.

- **Found a bug?**
  You can `Report bugs on Launchpad`_!

- **Want to give feedback?**
  If you have any comments, requests or suggestions that you'd like to share,
  we'd be very happy to receive them! Please feel free to reach out on
  `our Discourse forum`_, or you can get in touch via the ``#ubuntu-server``
  `IRC channel on Libera`_.

Project and community
=====================

Ubuntu Pro Client is a member of the Ubuntu family. It’s an open source project
that warmly welcomes community projects, contributions, suggestions, fixes and
constructive feedback.

- Read our `Code of conduct`_
- `Contribute`_

.. toctree::
   :hidden:
   :maxdepth: 2

   Tutorials <tutorials.rst>

.. toctree::
   :hidden:
   :maxdepth: 2
   
   How-to guides <howtoguides.rst>
   
.. toctree::
   :hidden:
   :maxdepth: 2

   Explanation <explanations.rst>

.. toctree::
   :hidden:
   :maxdepth: 2

   Reference <references.rst>

.. LINKS:
.. _Ubuntu Pro: https://ubuntu.com/pro
.. _Common Criteria EAL2 (CC EAL): https://ubuntu.com/security/cc
.. _compliance, certifications, and hardening: https://ubuntu.com/security/certifications
.. _(CIS) Benchmark: https://ubuntu.com/security/cis
.. _Ubuntu Security Guide: https://ubuntu.com/security/certifications/docs/usg
.. _Expanded Security Maintenance (ESM): https://ubuntu.com/security/esm
.. _a security assessment: https://ubuntu.com/contact-us/form?product=pro
.. _ROS ESM: https://ubuntu.com/robotics/ros-esm
.. _this introductory guide: https://discourse.ubuntu.com/t/ros-esm-user-introduction/26206
.. _FIPS 140-2 Certified Modules: https://ubuntu.com/security/fips
.. _Livepatch: https://ubuntu.com/security/livepatch
.. _Livepatch documentation: https://ubuntu.com/security/livepatch/docs
.. _list of supported kernels: https://ubuntu.com/security/livepatch/docs/livepatch/reference/kernels
.. _real-time kernel: https://ubuntu.com/realtime-kernel
.. _more information about real-time Ubuntu: https://ubuntu.com/kernel/real-time/contact-us
.. _Landscape: https://ubuntu.com/landscape
.. _Report bugs on Launchpad: https://bugs.launchpad.net/ubuntu-advantage-tools/+filebug
.. _Code of conduct: https://ubuntu.com/community/code-of-conduct
.. _Contribute: https://github.com/canonical/ubuntu-advantage-client/blob/main/CONTRIBUTING.md
.. _IRC channel on Libera: https://kiwiirc.com/nextclient/irc.libera.chat/ubuntu-server
.. _our Discourse forum: https://discourse.ubuntu.com/c/ubuntu-pro/116
.. _in our FAQ: https://discourse.ubuntu.com/t/ubuntu-pro-faq/34042
