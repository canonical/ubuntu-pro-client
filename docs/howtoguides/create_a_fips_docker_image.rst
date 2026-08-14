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

Create a Dockerfile
===================

Next, let us create a file named ``Dockerfile`` by running the following
command:

.. code-block:: bash

    touch Dockerfile

This file will later enable FIPS in the container, upgrade all the packages,
and install the FIPS version of ``openssl``.

Edit the file and add the following contents:

.. tab-set::

    .. tab-item:: Focal (20.04)
        
        .. code-block:: dockerfile

            FROM ubuntu:focal

            ENV DEBIAN_FRONTEND=noninteractive
            ENV OPENSSL_FORCE_FIPS_MODE=0

            # Mount the token file and attach explicitly
            RUN --mount=type=secret,id=pro-token \
                apt-get update -y && \
                apt-get install -y ubuntu-pro-client ca-certificates && \
                pro attach $(cat /run/secrets/pro-token) --no-auto-enable && \
                pro enable fips-updates --assume-yes && \
                apt-get update -y && \
                apt-get install -y openssl libssl1.1 libssl1.1-hmac libgcrypt20 libgcrypt20-hmac strongswan strongswan-hmac openssh-client openssh-server && \
                pro detach --assume-yes || true && \
                apt-get purge -y ubuntu-pro-client && \
                apt-get autoremove -y && \
                rm -rf /var/lib/apt/lists/*

            ENV OPENSSL_FORCE_FIPS_MODE=1

            CMD ["/bin/bash"]

    .. tab-item:: Jammy (22.04)

        .. code-block:: dockerfile

            FROM ubuntu:jammy

            ENV DEBIAN_FRONTEND=noninteractive
            ENV OPENSSL_FORCE_FIPS_MODE=0

            # Mount the token file and attach explicitly
            RUN --mount=type=secret,id=pro-token \
                apt-get update -y && \
                apt-get install -y ubuntu-pro-client ca-certificates && \
                pro attach $(cat /run/secrets/pro-token) --no-auto-enable && \
                pro enable fips-updates --assume-yes && \
                apt-get update -y && \
                apt-get install -y openssl openssl-fips-module-3 libgcrypt20 strongswan openssh-client libgnutls30 && \
                pro detach --assume-yes || true && \
                apt-get purge -y ubuntu-pro-client && \
                apt-get autoremove -y && \
                rm -rf /var/lib/apt/lists/*

            ENV OPENSSL_FORCE_FIPS_MODE=1

            CMD ["/bin/bash"]

    .. tab-item:: Noble (24.04)

        .. code-block:: dockerfile

            FROM ubuntu:noble

            ENV DEBIAN_FRONTEND=noninteractive
            ENV OPENSSL_FORCE_FIPS_MODE=0

            # Mount the token file and attach explicitly
            RUN --mount=type=secret,id=pro-token \
                apt-get update -y && \
                apt-get install -y ubuntu-pro-client ca-certificates && \
                pro attach $(cat /run/secrets/pro-token) --no-auto-enable && \
                pro enable fips-updates --assume-yes && \
                apt-get update -y && \
                apt-get install -y openssl openssl-fips-module-3 libgcrypt20 strongswan openssh-client libgnutls30t64 && \
                pro detach --assume-yes || true && \
                apt-get purge -y ubuntu-pro-client && \
                apt-get autoremove -y && \
                rm -rf /var/lib/apt/lists/*

            ENV OPENSSL_FORCE_FIPS_MODE=1

            CMD ["/bin/bash"]


Create a short-lived token and store it in a file:
======================================================
.. code-block:: bash

    sudo pro api u.pro.attach.guest.get_guest_token.v1 | jq -r '.data.attributes.guest_token' > pro-token.txt

.. note::

    The token is short-lived and will expire after a few minutes. If you are
    unable to build the Docker image in that time, you will need to create a
    new token.

Alternatively, we can use the permanent Ubuntu Pro token in the 
``pro-token.txt`` file if the host is not attached to Pro. This is however not recommended.

Build the Docker image
======================

Now let's build the docker image by running the following command:

.. code-block:: bash

    DOCKER_BUILDKIT=1 docker build . --secret id=pro-token,src=pro-token.txt -t <image-name>

This will pass the ``pro-token.txt`` file we created earlier as a
`BuildKit Secret`_ so that the finished Docker image will not contain your
Ubuntu Pro token.

Optionally, delete the ``pro-token.txt`` file after the build is complete:

.. code-block:: bash

    rm pro-token.txt

Test the Docker image
=====================

.. important::

    The Docker image isn't considered fully FIPS compliant unless it is running
    on a host Ubuntu machine that is also FIPS compliant.

Let's check to make sure the FIPS version of ``openssl`` is installed in the
container. First, let us run:

.. code-block:: bash

    docker image list
    docker run -it --rm <image-name> dpkg-query --show openssl

This should show something like: ``openssl	1.1.1f-1ubuntu2.fips.2.8`` (notice
"fips" in the version name).

We can now use the build Docker image's FIPS compliant ``openssl`` to connect
to ``https://ubuntu.com``:

.. code-block:: bash

    docker run -it --rm <image-name> sh -c "echo | openssl s_client -connect ubuntu.com:443"

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
