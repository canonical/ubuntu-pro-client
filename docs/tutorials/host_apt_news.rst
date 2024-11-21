.. _host-own-apt-news:

Host your own APT news
**********************

APT news is used to deliver messages related to APT updates. However, it can also be used to display custom messages within the ``apt upgrade`` command to your users.

In this tutorial, you will learn how to host your own APT news and how to
configure your Ubuntu machines to use it.

.. Why we use Multipass + command to install it
.. include:: ./common/install-multipass.txt

.. note::
   You will need at least 10 Gigabytes of free space on your machine to launch the Multipass VM used in this tutorial.

Tutorial overview
=====================

To demonstrate how APT news works, we will create three containers inside a
Multipass VM. We will configure one of them to be the APT news server, and we
will configure the other two to consume APT news from that server. It will
look something like this:

.. image:: host-apt-news.drawio.png
   :align: center

Command snippets throughout this tutorial will include a shell prompt to make
it clear on which machine the command will be executed.

.. list-table::
   :header-rows: 1

   * - Prompt
     - Machine
   * - ``you@yourcomputer:~$``
     - Your computer
   * - ``ubuntu@tutorial:~$``
     - Multipass VM named ``tutorial``
   * - ``root@apt-news-server:~#``
     - LXD container named ``apt-news-server``
   * - ``root@client-jammy:~#``
     - LXD container named ``client-jammy``
   * - ``root@client-focal:~#``
     - LXD container named ``client-focal``


Create the local VM and containers
==================================

Let's begin by launching an Ubuntu 24.04 Multipass VM with the following command:

.. code-block:: console

   you@yourcomputer:~$ multipass launch noble --disk 10G --name tutorial

Then we can access the VM using the ``multipass shell`` subcommand:

.. code-block:: console

   you@yourcomputer:~$ multipass shell tutorial

When you see "Welcome to Ubuntu 24.04 LTS" and the shell prompt changes to the
following, you know that you've entered the VM.

.. code-block:: console

   ubuntu@tutorial:~$

We're going to use `LXD`_ to set up our server and clients, so once we're inside the VM, we can set up LXD with the default parameters:

.. code-block:: console

   ubuntu@tutorial:~$ lxd init --minimal


Now we will launch three containers inside the VM with the following commands. This may
take a while since it will need to download the appropriate Ubuntu images.

.. code-block:: console

   ubuntu@tutorial:~$ lxc launch ubuntu-daily:noble apt-news-server
   ubuntu@tutorial:~$ lxc launch ubuntu-daily:jammy client-jammy
   ubuntu@tutorial:~$ lxc launch ubuntu-daily:focal client-focal

Configure the APT news server
=============================

Now, let's set up the ``apt-news-server`` container to serve APT news content.
APT news content is formatted as a JSON file and served over HTTP(S). We can
accomplish this by installing and configuring `nginx`_ to serve a properly
formatted JSON file.

First, enter the ``apt-news-server`` container:

.. code-block:: console

   ubuntu@tutorial:~$ lxc shell apt-news-server
   root@apt-news-server:~#

Inside ``apt-news-server``, install ``nginx`` via ``apt``. This will also start the HTTP server on port 80.

.. code-block:: console

   root@apt-news-server:~# apt install -y nginx

With ``nginx`` installed and running, we can author an APT news JSON file. Open ``/var/www/html/aptnews.json``:

.. code-block:: console

   root@apt-news-server:~# nano /var/www/html/aptnews.json

and add the following content:

.. code-block:: json

   {
     "messages": [
       {
         "begin": "TODAY",
         "selectors": {
           "codenames": ["jammy"]
         },
         "lines": [
           "Hello 22.04 users!",
           "This is the APT news server."
         ]
       },
       {
         "begin": "TODAY",
         "lines": [
           "Hello everyone else!",
           "This is the APT news server."
         ]
       }
     ]
   }

In ``nano``, use :kbd:`CTRL` + :kbd:`S` and :kbd:`CTRL` + :kbd:`X` to save and exit, respectively.

That apt news configuration will show one message to systems running Ubuntu
22.04 (codename "jammy") and will show a different message to all other systems.

The value of ``"begin"`` actually needs to be an ISO8601 formatted datetime
string, and the message won't be shown before the ``begin`` date or more than 30
days after the ``begin`` date. For the purposes of this tutorial you can
quickly replace "TODAY" with today's date in ``aptnews.json`` with the
following command.

.. code-block:: console

   root@apt-news-server:~# sed -i "s/TODAY/$(date --iso-8601=seconds)/" /var/www/html/aptnews.json

You can double check that the command worked by looking at the new contents of the file.

.. code-block:: console

   root@apt-news-server:~# cat /var/www/html/aptnews.json

You should see that the ``begin`` field now has an appropriate value.

.. code-block:: json
   :force:
   :class: ignore-err
   :emphasize-lines: 4

   {
     "messages": [
       {
         "begin": "2024-07-30T16:35:19+00:00",
         "selectors": {
           "codenames": ["jammy"]
   ...

Now that our ``apt-news-server`` is configured, we can exit that container:

.. code-block:: console

   root@apt-news-server:~# exit
   ubuntu@tutorial:~$


Configure the client machines to use the APT news server
========================================================

We need to configure both client machines to use the APT news server we just
created. This is a single command on each container that we can run using
``lxc exec``:

.. code-block:: console

   ubuntu@tutorial:~$ lxc exec client-jammy -- pro config set apt_news_url=http://apt-news-server/aptnews.json
   ubuntu@tutorial:~$ lxc exec client-focal -- pro config set apt_news_url=http://apt-news-server/aptnews.json

That's it! Now those containers will start displaying APT news in the output of ``apt upgrade``.

Normally, the containers would fetch the latest APT news whenever an
``apt update`` is run, but at most once per day. For this tutorial, we'll use
``pro refresh messages`` to force the containers to fetch the latest news
right away.

In the Jammy container we expect to see the special message we set up for systems on
Ubuntu 22.04. Let's check this is working correctly by first entering the Jammy container:

.. code-block:: console

   ubuntu@tutorial:~$ lxc shell client-jammy

Then we can run these commands to see the custom APT news message:

.. code-block:: console

   root@client-jammy:~# pro refresh messages
   root@client-jammy:~# apt upgrade

The output of ``apt upgrade`` should look like this.

.. code-block:: text

   Reading package lists... Done
   Building dependency tree... Done
   Reading state information... Done
   Calculating upgrade... Done
   #
   # Hello 22.04 users!
   # This is the APT news server.
   #
   0 upgraded, 0 newly installed, 0 to remove and 0 not upgraded.

Since this is what we expected, we can now exit the container:

.. code-block:: console

   root@client-jammy:~# exit
   ubuntu@tutorial:~$

In the Focal client container we expect to see the other message. Let's check that
by entering the Focal container:

.. code-block:: console

   ubuntu@tutorial:~$ lxc shell client-focal

Then run these commands again to see the APT news message:

.. code-block:: console

   root@client-focal:~# pro refresh messages
   root@client-focal:~# apt upgrade

The output of ``apt upgrade`` should look like this.

.. code-block:: text

   Reading package lists... Done
   Building dependency tree... Done
   Reading state information... Done
   Calculating upgrade... Done
   #
   # Hello everyone else!
   # This is the APT news server.
   #
   0 upgraded, 0 newly installed, 0 to remove and 0 not upgraded.

Once again, this is exactly what we expected to see, so everything is working correctly! Now we can exit this container:

.. code-block:: console

   root@client-focal:~# exit
   ubuntu@tutorial:~$

Clean up
========

Congratulations! This tutorial demonstrated the basics of how an APT news server can be set up and used by other Ubuntu machines.

Now that the tutorial is over, you can exit out of the Multipass VM:

.. code-block:: console

   ubuntu@tutorial:~$ exit
   you@yourcomputer:~$

and delete it:

.. code-block:: console

   you@yourcomputer:~$ multipass delete --purge tutorial

.. LINKS
.. include:: ../links.txt

.. _Multipass: https://multipass.run/
.. _LXD: https://documentation.ubuntu.com/lxd/
.. _nginx: https://nginx.org/
