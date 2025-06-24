.. _tutorial-fips-docker-image:

Create an Ubuntu FIPS Docker image
**********************************

.. note::

    This tutorial requires at least Ubuntu Pro Client version 27.7 -- to check
    which version of the Pro Client you are using, run ``pro version``.

Acquire your Ubuntu Pro token
=============================

You can acquire an Ubuntu Pro token one of two ways, either by logging in to
your Ubuntu Pro account or by using the Ubuntu Pro Client on an already
attached machine.

Logging in to your Ubuntu Pro account
-------------------------------------

Your Ubuntu Pro token can be found on your Ubuntu Pro dashboard. To access your
dashboard, you need an `Ubuntu One`_ account. If you purchased an Ubuntu Pro
subscription and don't yet have an Ubuntu One account, be sure to use the same
email address you used to purchase your subscription. If you haven't purchased
an Ubuntu Pro subscription, don't worry! Everyone gets a free token for
personal use with their Ubuntu One account -- no purchase necessary.

The Ubuntu One account functions as a Single Sign On (SSO), so after you log in
we can go straight to the `Ubuntu Pro dashboard <Pro_>`_. Here, you should see
a list of your subscriptions (including the "free for personal use"
subscription) in the left-hand column.

Click on the subscription that you wish to use for this tutorial, if it is not
already selected. On the right you will now see the details of your
subscription, including your secret token (under the "Subscription" header and
next to the "🔗" symbol).

Ubuntu Pro Client on an already attached machine
------------------------------------------------

If you will be building this Docker image on a machine that is already attached
to an Ubuntu Pro subscription, you can use the Ubuntu Pro Client to get a guest
token for the Docker build.

.. code-block:: bash

   sudo pro api u.pro.attach.guest.get_guest_token.v1

That command will output JSON that includes a guest token that is valid for a
short time, during which you can use it in your Docker build.

.. tip::
   If you have ``jq`` installed, you can use the following command to extract the token:
    
   .. code-block:: bash
    
      sudo pro api u.pro.attach.guest.get_guest_token.v1 | jq -r '.data.attributes.guest_token'

.. caution:

    The Ubuntu Pro token must be kept secret. It is used to uniquely identify
    your Ubuntu Pro subscription.

Create an Ubuntu Pro Client attach config file
==============================================

First, let's create a directory for this tutorial and navigate there.

.. code-block:: bash

    mkdir pro_fips_tutorial
    cd pro_fips_tutorial

Now we need to create our config file called ``pro-attach-config.yaml``:

.. code-block:: bash

    touch pro-attach-config.yaml

Edit the file, add the following contents, and save it:

.. code-block:: yaml

    token: YOUR_TOKEN
    enable_services:
    - fips

Replace ``YOUR_TOKEN`` with the Ubuntu Pro token we got from the Ubuntu Pro
`dashboard <Pro_>`_ earlier.

Create a Dockerfile
===================

Next, let us create a file named ``Dockerfile`` by running the following
command:

.. code-block:: bash

    touch Dockerfile

This file will later enable FIPS in the container, upgrade all the packages,
and install the FIPS version of ``openssl``.

Edit the file and add the following contents:

.. code-block:: dockerfile

    FROM ubuntu:focal

    RUN --mount=type=secret,id=pro-attach-config \
        apt-get update \
        && apt-get install --no-install-recommends -y ubuntu-pro-client ca-certificates \
        && pro attach --attach-config /run/secrets/pro-attach-config \
        && apt-get upgrade -y \
        && apt-get install -y openssl libssl1.1 libssl1.1-hmac libgcrypt20 libgcrypt20-hmac strongswan strongswan-hmac openssh-client openssh-server \
        && pro detach --assume-yes \
        && apt-get purge --auto-remove -y ubuntu-pro-client ca-certificates \
        && rm -rf /var/lib/apt/lists/*

.. hint::

    For more details on how this works, see our how-to guide on enabling
    :ref:`Ubuntu Pro Services in a Dockerfile <enable_in_dockerfile>`.

Build the Docker image
======================

Now let's build the docker image by running the following command:

.. code-block:: bash

    DOCKER_BUILDKIT=1 docker build . --secret id=pro-attach-config,src=pro-attach-config.yaml -t ubuntu-focal-fips

This will pass the ``pro-attach-config.yaml`` file we created earlier as a
`BuildKit Secret`_ so that the finished Docker image will not contain your
Ubuntu Pro token.

Test the Docker image
=====================

.. important::

    The Docker image isn't considered fully FIPS compliant unless it is running
    on a host Ubuntu machine that is also FIPS compliant.

Let's check to make sure the FIPS version of ``openssl`` is installed in the
container. First, let us run:

.. code-block:: bash

    docker run -it ubuntu-focal-fips dpkg-query --show openssl

This should show something like: ``openssl	1.1.1f-1ubuntu2.fips.2.8`` (notice
"fips" in the version name).

We can now use the build Docker image's FIPS compliant ``openssl`` to connect
to ``https://ubuntu.com``:

.. code-block:: bash

    docker run -it ubuntu-focal-fips sh -c "echo | openssl s_client -connect ubuntu.com:443"

This should print information about the certificates of ubuntu.com and the
algorithms used during the TLS handshake.

Success
=======

That's it! You could now push this image to a private registry and use it as
the base of other Docker images using ``FROM``.

If you want to learn more about how the steps in this tutorial work, take a
look at the more general how-to guide on enabling
:ref:`Ubuntu Pro services in a Dockerfile <enable_in_dockerfile>`.

.. LINKS

.. include:: ../links.txt

.. _BuildKit Secret: https://docs.docker.com/engine/reference/builder/#run---mounttypesecret
