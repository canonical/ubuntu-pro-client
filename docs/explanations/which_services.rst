.. _which-services:

Which services are for me?
**************************

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
         support through `Expanded Security Maintenance (ESM) <esm_>`_. We recommend
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
           :ref:`how to enable it<manage-livepatch>` with ``pro``.

       * **Landscape**

         `Landscape`_ is the leading management and administration tool for
         Ubuntu. It can manage up to 40,000 Ubuntu machines with a single
         interface, and can automate security patching, as well as hardening
         and compliance. Landscape can be `self-hosted`_ or you can use Canonical's
         `Landscape SaaS`_ offering.

         * Find out more about
           :ref:`registering a machine with Landscape<manage-landscape>`
           using ``pro``.

       Want more information?

    .. tab-item:: Security certification

       Ubuntu provides security `compliance, certifications, and hardening <certifications_>`_:

       * **FIPS 140-2**

         * `FIPS 140-2 Certified Modules <fips_>`_ are available through ``fips``.

         * Compliant but non-certified patches are available through
           ``fips-updates``.

         * Find out more :ref:`about managing FIPS<manage-fips>`.

       * **Ubuntu Security Guide (USG)**

         * In the 20.04 LTS we introduced the `Ubuntu Security Guide <usg_>`_, which
           provides security tooling through ``usg``. It bundles together
           multiple key components, such as CIS benchmarking and DISA-STIG.

         * Before USG, Center for Internet Security `(CIS) Benchmark <cis_>`_ tooling
           was available as a separate service through ``cis``. This can be
           used up to (and including) 20.04 LTS, but on all later LTS releases
           this functionality is provided through ``usg``.

         * Find out :ref:`how to manage USG (and CIS)<manage-cis>`
           with the Pro Client.

       * **Common Criteria**

         * `Common Criteria EAL2 (CC EAL) <CC_>`_ certification tooling is available
           through ``cc-eal``. The Ubuntu 18.04 LTS and 16.04 LTS have both
           been certified.

         * Find out :ref:`how to enable CC EAL<manage-cc>` on your LTS.

       Want more information?

    .. tab-item:: Personal user

       * **Expanded Security Maintenance (ESM)**

         If you're using Pro on an LTS machine (Desktop or Server) you can get
         additional security support through
         `Expanded Security Maintenance (ESM) <esm_>`_. We recommend it for everyone
         using Pro, and it's enabled by default. It includes two services:

         * ``esm-infra`` provides security updates for packages in the Ubuntu
           'main' repository (packages from Ubuntu) for five additional years
           beyond the standard five years of security maintenance of 'main'
           packages.

         * ``esm-apps`` covers packages in the 'universe' repository (which
           are from Debian and the community) for ten years after the LTS
           release. 

         * Read more
           :ref:`about ESM-Apps and ESM-Infra<expl-ESM>`.

       * **Livepatch**

         Ubuntu `Livepatch`_ removes the need to immediately reboot your
         machine after a patch is applied to the kernel, so you can perform
         device reboots when it's convenient for you. Although it's
         lightweight, it may not be suitable on a very small system with
         limited memory. Check our `list of supported kernels`_ if you're
         unsure.

         * Find out
           :ref:`how to enable Livepatch<manage-livepatch>`.

       Want more information?

    .. tab-item:: Specialty services

       * **ROS ESM**

         Our Robot Operating System Expanded Security Maintenance (`ROS ESM`_)
         service provides security maintenance for ROS LTS releases, starting
         with ROS Kinetic on Ubuntu 16.04 -- including packages from the Ubuntu
         'universe' repository.

         * ``ros`` provides security updates to the 600+ packages for ROS 1
           Kinetic and Melodic, and ROS 2 Foxy -- in addition to the security
           coverage already provided by ESM. 

         * ``ros-updates`` also gives you access to non-security updates.

         * Want to know how to enable ROS ESM? Check out
           `this introductory guide`_ by the ROS team to get started.

       * **Real-time kernel**

         The Ubuntu 22.04 LTS brought the new, enterprise-grade
         `real-time kernel <realtime_>`_, which reduces kernel latencies and ensures
         predictable performance for time-sensitive task execution. It was
         designed to deliver stable, ultra-low latency and security for
         critical telco infrastructure, but has applications across a wide
         variety of industries.

         * Find out `more information about real-time Ubuntu`_ and what it can
           do for your organisation. 

         * Or see our guide on
           :ref:`how to enable the real-time kernel<manage-realtime>`. 

       Want more information?
       
.. LINKS

.. include:: ../links.txt

.. _a security assessment: https://ubuntu.com/contact-us/form?product=pro
.. _this introductory guide: https://discourse.ubuntu.com/t/ros-esm-user-introduction/26206
.. _Livepatch documentation: https://ubuntu.com/security/livepatch/docs
.. _list of supported kernels: https://ubuntu.com/security/livepatch/docs/livepatch/reference/kernels
.. _self-hosted: https://ubuntu.com/landscape/pricing
.. _Landscape SaaS: https://ubuntu.com/landscape/pricing
.. _more information about real-time Ubuntu: https://ubuntu.com/kernel/real-time/contact-us

