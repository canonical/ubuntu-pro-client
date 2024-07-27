.. _explanation:

Ubuntu Pro Client explanation
*****************************

Our explanatory and conceptual guides are written to provide a better
understanding of how the Ubuntu Pro Client (``pro``) works. They enable you
to expand your knowledge and become better at using and configuring ``pro``.

Messaging
=========

Here you'll find details about Ubuntu Pro Client-related APT and MOTD messages
-- what they are, when they are used and how they work.

..  toctree::
    :maxdepth: 1

    Pro-related APT messages <explanations/apt_messages.md>
    Pro-related MOTD messages <explanations/motd_messages.md>

Commands
========

Some of the commands in ``pro`` do more than you think. Here we'll show you a
selection of some of the commands -- what they do, and how they work.

..  toctree::
    :maxdepth: 1

    explanations/how_to_interpret_the_security_status_command.md
    explanations/how_to_interpret_output_of_unattended_upgrades.md
    explanations/status_columns.md
    explanations/what_refresh_does.md
    explanations/purging_services.md

Public Cloud Ubuntu Pro
=======================

Here we talk about Ubuntu Pro images for AWS, Azure and GCP, and the related
tooling: the ``ubuntu-pro-auto-attach`` package.

..  toctree::
    :maxdepth: 1

    explanations/what_are_ubuntu_pro_cloud_instances.md
    explanations/what_is_the_ubuntu_advantage_pro_package.md


Handling CVEs and USNs
==============================

In this section we explain the output of ``pro fix`` and its API interface
as well as some details related to it like CVEs and USNs.

..  toctree::
    :maxdepth: 1

    explanations/cves_and_usns_explained.md
    explanations/fix_scenarios.rst
    explanations/how_to_interpret_output_of_fix_plan_api.md

Other Pro features explained
============================

..  toctree::
    :maxdepth: 1

    explanations/which_services.rst
    explanations/about_esm.md
    explanations/what_are_the_timer_jobs.md
    explanations/using_pro_offline.rst
    explanations/what_is_the_daemon.md
    explanations/errors_explained.md
    explanations/deprecation_policy.rst
    explanations/data_collection.rst
    explanations/pro_token_and_machine_usage.rst

