.. _pro_token_and_machine_usage:

Machine counts and token usage for Ubuntu Pro
*********************************************

Ubuntu Pro tokens are used to authenticate your machine and enable access to the services you are entitled to. These tokens are unique and specific to your account, so you should treat them as a secret (as you would with a password).

In this page, we'll discuss how Ubuntu Pro tokens work and how machines are counted against your subscription.

About Ubuntu Pro tokens
-----------------------

- **Obtaining Pro tokens**:
  After subscribing to Ubuntu Pro, you can access your subscriptions through the `Ubuntu Pro Dashboard <Pro_dashboard_>`_. Each subscription includes an Ubuntu Pro token that can be used to attach as many machines as your subscription allows.

- **Attaching Pro tokens**:
  You can use the ``sudo pro attach`` command to connect a machine to your Ubuntu Pro subscription. 

- **Detaching Pro tokens**:
  You can use the ``sudo pro detach`` command to remove a machine from the subscription. If you are attached on a VM you intend to delete, the token does not need to be detached before the VM is destroyed.

For more detailed information regarding Pro commands, refer to our :ref:`Getting started with Ubuntu Pro client <tutorial-commands>` tutorial.

Monitoring active machines
--------------------------

Active machines are counted based on the number of machines attached to your subscription at a given time. An active machine is defined as a machine that has been attached to a given subscription at any point within the past 24 hours.

Each subscription type has a limit on the number of machines it can cover. For personal subscriptions, this limit is 5 physical machines with unlimited VMs on these machines. Enterprise subscriptions will have a higher limit and may differentiate between physical and virtual machines.

The Ubuntu Pro dashboard can help track the number of active machines, ensuring compliance with subscription limits. It provides a comprehensive view of all active and attached machines. It helps track the number of active machines, ensuring that you remain within the subscription limits.

Dealing with multiple VMs
-------------------------

In an IaaS environment where node control is limited, you can contact `Canonical's sales team <pro_sales_form_>`_ to discuss purchasing licenses per single VM rather than per physical node.


Handling overage of active machines
-----------------------------------

Canonical monitors the number of active machines associated with your Ubuntu Pro subscription. It's important to ensure that the number of active machines does not exceed your subscription limit. However, occasional overages are generally acceptable and will not immediately impact your Ubuntu Pro subscription. If persistent overages occur, Canonical may reach out to address the issue. 
To avoid any disruptions, you can monitor your active machines and detach any that are no longer in use. 

If you have any additional questions, please visit the `Ubuntu Pro FAQ <FAQ_>`_ for further information.

.. LINKS

.. include:: ../links.txt