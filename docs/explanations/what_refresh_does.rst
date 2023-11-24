.. _expl-pro-refresh:

What ``pro refresh`` does
*************************

When you run the ``pro refresh`` command on your machine, three distinct stages
are performed.

Contract
========

First, the contract information on the machine is refreshed. If we find any
difference between the old contract and the new one, we process those
differences and apply any changes to the machine.

If you need **only** this stage during refresh, run ``pro refresh contract``.

Configuration
=============

If there is any config change made to ``/etc/ubuntu-advantage/uaclient.conf``,
those changes will now be applied to the machine.

If you need **only** this stage during refresh, run ``pro refresh config``.

MOTD and APT messages
=====================

Processes new Message of the Day (MOTD) and Advanced Packaging Tool (APT)
messages, and refreshes the machine to use them.

If you need **only** this stage during refresh, run ``pro refresh messages``.
