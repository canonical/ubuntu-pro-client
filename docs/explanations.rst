.. _explanation:

Ubuntu Pro Client explanation
*****************************

Our explanatory and conceptual guides are written to provide a better
understanding of how the Ubuntu Pro Client (``pro``) works. They enable you
to expand your knowledge and become better at using and configuring ``pro``.

Pro services
============

Ubuntu Pro is a portal to many other services offered by Canonical. Here you
can discover more about the services available through Pro and how you can
manage them with the Pro Client.

* Find out :ref:`which services we recommend <which-services>` for different
  situations
* Use the ``pro status`` command
  :ref:`to monitor active services <pro-status-output>` on your machine
* Learn :ref:`about ESM <expl-ESM>` security services (``esm-apps`` and
  ``esm-infra``)
* :ref:`disable_and_purge` explains how to disable services and remove them
  from your machine

..  toctree::
    :maxdepth: 1
    :hidden:

    explanations/which_services.rst
    Checking active services <explanations/status_columns.rst>
    explanations/about_esm.rst
    explanations/purging_services.rst

Handling security vulnerabilities
=================================

Ubuntu Pro provides security fixes for vulnerabilities (CVEs and USNs). This
section explains what those are, how to find out if your machine is affected,
and the different uses of the ``pro fix`` command.

* :ref:`About CVEs and USNs <expl-cve-usn>`
* :ref:`Understand the security coverage <pro-security-status>` on your
  installed packages using ``pro security-status``
* :ref:`Common scenarios <pro-fix-howto>` when using the ``pro fix`` command

..  toctree::
    :maxdepth: 1
    :hidden:

    About CVEs and USNs <explanations/cves_and_usns_explained.rst>
    Monitoring security coverage <explanations/how_to_interpret_the_security_status_command.rst>
    Using pro fix to solve CVEs/USNs <explanations/fix_scenarios.rst>

Public Cloud Ubuntu Pro
=======================

Ubuntu Pro is supported on AWS, Azure and GCP through Public Cloud Ubuntu Pro
images. On Pro Cloud images, machines are automatically attached to a support
contract by the Ubuntu Pro daemon.

* :ref:`Public Cloud Ubuntu Pro images <expl-about-pro-cpc>` and the auto-attach process
* :ref:`About the Pro daemon <the-pro-daemon>`

..  toctree::
    :maxdepth: 1
    :hidden:

    Public Cloud Ubuntu Pro images <explanations/what_are_ubuntu_pro_cloud_instances.rst>
    About the Pro daemon <explanations/what_is_the_daemon.rst>

Ubuntu Pro policies
===================

Here we explain our usage policies for features such as using Pro offline or
airgapped, how machines are counted against tokens, how we deprecate features
and what data is collected from active machines.

* :ref:`Using Ubuntu Pro airgapped or offline <pro-airgapped>`
* :ref:`How machines are counted <pro_token_and_machine_usage>`
* :ref:`Feature deprecation policy <deprecation-policy>`
* :ref:`Data collection policy <what-data-is-collected>`

..  toctree::
    :maxdepth: 1
    :hidden:

    Ubuntu Pro airgapped/offline <explanations/using_pro_offline.rst>
    How machines are counted <explanations/pro_token_and_machine_usage.rst>
    Feature deprecation policy <explanations/deprecation_policy.rst>
    Data collection policy <explanations/data_collection.rst>

Messaging
=========

Here you'll find details about Ubuntu Pro Client-related APT and MOTD messages
-- what they are, when they are used and how they work.

* :ref:`apt-messages`
* :ref:`motd-messages`
* :ref:`expl-timer-jobs`

..  toctree::
    :maxdepth: 1
    :hidden:

    Pro-related APT messages <explanations/apt_messages.rst>
    Pro-related MOTD messages <explanations/motd_messages.rst>
    explanations/what_are_the_timer_jobs.rst

API endpoints explained
========================

Some of the commands in ``pro`` do more than you think. Here we'll show some of
the API endpoint outputs and how to interpret them.

..  toctree::
    :maxdepth: 1
    
    The unattended-upgrades endpoint <explanations/how_to_interpret_output_of_unattended_upgrades.rst>
    The fix plan endpoint <explanations/how_to_interpret_output_of_fix_plan_api.rst>

