.. _manage-realtime:

How to manage real-time kernel
******************************

Pre-requisites
==============

The `real-time kernel <realtime_>`_ is currently supported on Ubuntu
22.04 LTS (Jammy) and 24.04 LTS (Noble). For more information, feel free to
`contact our real-time team`_.

Enable and install
==================

.. important:: 

    Once you enable real-time kernel, enabling some Pro services will not be
    possible. For a complete view of which services are compatible with
    real-time kernel, refer to the
    :doc:`services compatibility matrix <../references/compatibility_matrix>`.

Refer to the `Real-time Ubuntu documentation`_ for instructions on how to enable
the real-time kernel on Ubuntu Pro.

Notes
=====

* Real-time kernel is not compatible with Livepatch. If you wish to use the
  real-time kernel but Livepatch is enabled, ``pro`` will warn you and offer
  to disable Livepatch first.

.. LINKS

.. include:: ../links.txt

.. _contact our real-time team: https://ubuntu.com/kernel/real-time/contact-us
.. _Real-time Ubuntu documentation: https://canonical-real-time-ubuntu-documentation.readthedocs-hosted.com/en/latest/how-to/enable-real-time-ubuntu/
