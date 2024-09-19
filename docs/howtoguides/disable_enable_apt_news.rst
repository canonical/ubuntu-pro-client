.. _disable_enable_apt_news:

How to disable or re-enable APT News
************************************

APT News is a feature that allows for timely package-related news to be
displayed during an ``apt upgrade``. It is distinct from
:doc:`Ubuntu Pro 'available update' messages<../explanations/apt_messages>`
that are also displayed during an ``apt upgrade``. APT News messages are
fetched from https://motd.ubuntu.com/aptnews.json once per day (at most).

By default, APT News is turned on. In this guide, we show how to turn off and
on the APT News feature for a particular machine.

Check current APT News configuration
====================================

.. code-block:: bash

    pro config show apt_news

The default value is ``True``, so if you haven't yet modified this setting,
you will see:

.. code-block:: bash

    apt_news True

Disable APT News
================

.. code-block:: bash

    pro config set apt_news=false

This should also clear any current APT News you may be seeing on your system
during ``apt upgrade``.

You can double-check that the setting was changed successfully by running
``pro config show apt_news`` again. This time, you should see:

.. code-block:: bash

    apt_news False

Re-enable APT News (optional)
=============================

If you change your mind and want APT News to start appearing again during
``apt upgrade``, run the following command:

.. code-block:: bash

    pro config set apt_news=true

Once again, you can verify the setting worked with
the ``pro config show apt_news`` command.
