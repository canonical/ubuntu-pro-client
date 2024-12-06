.. _explanation:

Explanation
***********

Our explanatory and conceptual guides are written to provide a better
understanding of how the Ubuntu Pro Client (``pro``) works. They enable you
to expand your knowledge and become better at using and configuring ``pro``.

Pro services
============

.. include:: explanations/index_services.rst
   :start-line: 4
   :end-before: .. TOC

.. toctree::
   :maxdepth: 2
   :hidden:
   
   Pro services... <explanations/index_services>

Handling security vulnerabilities
=================================

.. include:: explanations/index_security.rst
   :start-line: 4
   :end-before: .. TOC

.. toctree::
   :maxdepth: 2
   :hidden:
   
   Security... <explanations/index_security>

Ubuntu Pro policies
===================

.. include:: explanations/index_policies.rst
   :start-line: 4
   :end-before: .. TOC

.. toctree::
   :maxdepth: 2
   :hidden:
   
   Policies... <explanations/index_policies>

Messaging
=========

.. include:: explanations/index_messages.rst
   :start-line: 4
   :end-before: .. TOC

.. toctree::
   :maxdepth: 2
   :hidden:
   
   Messages... <explanations/index_messages>

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

API endpoints explained
========================

Some of the commands in ``pro`` do more than you think. Here we'll show some of
the API endpoint outputs and how to interpret them.

..  toctree::
    :maxdepth: 1
    
    The unattended-upgrades endpoint <explanations/how_to_interpret_output_of_unattended_upgrades.rst>
    The fix plan endpoint <explanations/how_to_interpret_output_of_fix_plan_api.rst>

