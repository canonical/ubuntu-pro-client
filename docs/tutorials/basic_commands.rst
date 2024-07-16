.. _tutorial-commands:

Get started with Ubuntu Pro Client
**********************************

The Ubuntu Pro Client (``pro``) provides a simple mechanism for viewing,
enabling and disabling Canonical offerings on your system. In this tutorial, we
will cover the base ``pro`` commands that help you to successfully manage Pro
on your machine.

Main ``pro`` commands
=====================

When dealing with ``pro`` through the command line, there are six commands that
cover the main functions of the tool. They are:

* ``status``
* ``attach``
* ``refresh``
* ``detach``
* ``enable``
* ``disable``

In this tutorial, we will go through each of these commands and learn how to
properly use them. To achieve this without making any modifications to your
machine, we will use a Xenial Multipass virtual machine (VM).

.. Why we use Multipass + command to install it
.. include:: ./common/install-multipass.txt

.. Commands for launching and updating a Xenial VM
.. include:: ./common/create-vm.txt


Base ``pro`` commands
=====================

status
------

The ``status`` command of ``pro`` will show you the status of any Ubuntu Pro
service on your machine. It also helps you to easily verify that your machine
is attached to an Ubuntu Pro subscription.

Let's run it on our VM:

.. code-block:: bash

    $ pro status

You can expect to see an output similar to this:

.. code-block:: text

    SERVICE          AVAILABLE  DESCRIPTION
    cc-eal           yes        Common Criteria EAL2 Provisioning Packages
    cis              yes        Security compliance and audit tools
    esm-apps         yes        Expanded Security Maintenance for Applications
    esm-infra        yes        Expanded Security Maintenance for Infrastructure
    fips             yes        NIST-certified core packages
    fips-updates     yes        NIST-certified core packages with priority security updates
    livepatch        yes        Canonical Livepatch service
    ros              yes        Security Updates for the Robot Operating System
    ros-updates      yes        All Updates for the Robot Operating System

You can see that the ``status`` command shows the services available to your
machine, while also presenting a short description for each service.

If you also look at the last lines of the output, you can see that this machine
is not currently attached to an Ubuntu Pro subscription.

.. code-block:: text

    This machine is not attached to an Ubuntu Pro subscription.
    See https://ubuntu.com/pro


attach
------

We have seen which service offerings are available to us, but to access them we
first need to attach an Ubuntu Pro subscription. We can do this by running the
``attach`` command.

.. code-block:: bash

    $ sudo pro attach
    
You should see output like this, giving you a link and a code:

.. code-block:: bash

    ubuntu@test:~$ sudo pro attach
    Initiating attach operation...

    Please sign in to your Ubuntu Pro account at this link:
    https://ubuntu.com/pro/attach
    And provide the following code: H31JIV

Open the link without closing your terminal window. 

In the field that asks you to enter your code, copy and paste the code shown
in the terminal. Then, choose which subscription you want to attach to. 
By default, the Free Personal Token will be selected, which is fine for the
purposes of this tutorial.

Once you have pasted your code and chosen the subscription you want to attach
your machine to, click on the "Submit" button.

The attach process will then continue in the terminal window, and you should
eventually be presented with the following message:

.. code-block:: text

    Enabling default service esm-apps
    Updating package lists
    Ubuntu Pro: ESM Apps enabled
    Enabling default service esm-infra
    Updating package lists
    Ubuntu Pro: ESM Infra enabled
    Enabling default service livepatch
    Installing canonical-livepatch snap
    Canonical livepatch enabled.
    This machine is now attached to 'USER ACCOUNT'

    SERVICE          ENTITLED  STATUS    DESCRIPTION
    cc-eal           yes       disabled  Common Criteria EAL2 Provisioning Packages
    cis              yes       disabled  Security compliance and audit tools
    esm-apps         yes       enabled   Expanded Security Maintenance for Applications
    esm-infra        yes       enabled   Expanded Security Maintenance for Infrastructure
    fips             yes       disabled  NIST-certified core packages
    fips-updates     yes       disabled  NIST-certified core packages with priority security updates
    livepatch        yes       enabled   Canonical Livepatch service
    ros              yes       disabled  Security Updates for the Robot Operating System
    ros-updates      yes       disabled  All Updates for the Robot Operating System

    NOTICES
    Operation in progress: pro attach

    Enable services with: pro enable <service>

                    Account: USER ACCOUNT
            Subscription: USER SUBSCRIPTION
                Valid until: 9999-12-31 00:00:00+00:00
    Technical support level: essential


From this output, we can see that the ``attach`` command has introduced the
"status" column. This shows which services (specified by your user
subscription) have been enabled by default.

After the command ends, ``pro`` displays the new state of the machine. This
status output is exactly what you see if you run the ``status`` command. Let's
confirm this by running the ``status`` command again:

.. code-block:: bash

    $ pro status


.. note::

    You may be wondering why the output of ``status`` is different depending on
    whether ``pro`` is attached or unattached. For more information on why this
    is, refer to our
    :ref:`explanation on the different columns<pro-status-output>`.


Finally, another useful bit at the end of the output for both ``attach`` and
``status`` is the contract expiration date:

.. code-block::

        Account: USER ACCOUNT
    Subscription: USER SUBSCRIPTION
    Valid until: 9999-12-31 00:00:00+00:00


The ``Valid until`` field describes when your contract will expire, so you can
be aware of when it needs to be renewed. Note that if you are using a free
token, you will not see this part of the output since free tokens never expire.

refresh
-------

Although *free* tokens never expire, if you buy an Ubuntu Pro subscription and
later need to renew your contract, how can you make your machine aware of it?

This is where the ``refresh`` command comes in:

.. code-block:: bash

    $ sudo pro refresh

This command will "refresh" the contract on your machine. It's also really
useful if you want to change any definitions on your subscription. 

For example, let's assume that you now want ``cis`` to be enabled by default
when attaching. After you modify your subscription on the Ubuntu Pro website to
enable it by default, running the refresh command will process the changes you
made, and ``cis`` will then be enabled.

.. hint::

    The ``refresh`` command does more than just update the contract in your
    machine. If you would like more information about the command, take a look
    at :ref:`this deeper explanation<expl-pro-refresh>`.

enable
------

There is another way to enable a service that wasn't activated during
``attach`` or ``refresh``. Let us suppose that you now want to enable ``cis``
on the machine manually. To achieve this, you can use the ``enable`` command.

Let's try enabling ``cis`` on our VM by running:

.. code-block:: bash

    $ sudo pro enable cis

After running the command, you should see output similar to this:

.. code-block:: text

    One moment, checking your subscription first
    Updating package lists
    Installing CIS Audit packages
    CIS Audit enabled
    Visit https://ubuntu.com/security/cis to learn how to use CIS


We can then confirm that ``cis`` is now enabled by using the ``status`` command
again:

.. code-block:: bash

    $ pro status

And you should see:

.. code-block:: text

    SERVICE          ENTITLED  STATUS    DESCRIPTION
    cc-eal           yes       disabled  Common Criteria EAL2 Provisioning Packages
    cis              yes       enabled   Security compliance and audit tools
    esm-apps         yes       enabled   Expanded Security Maintenance for Applications
    esm-infra        yes       enabled   Expanded Security Maintenance for Infrastructure
    fips             yes       disabled  NIST-certified core packages
    fips-updates     yes       disabled  NIST-certified core packages with priority security updates
    livepatch        yes       enabled   Canonical Livepatch service
    ros              yes       disabled  Security Updates for the Robot Operating System
    ros-updates      yes       disabled  All Updates for the Robot Operating System

We can see now that ``cis`` is marked as ``enabled`` under "status".

disable
-------

What happens if you don't want a service anymore?

All you need to do is disable that service through ``pro``. For example, let's
say we changed our mind about ``cis`` after enabling it, and we now want to
disable it instead. We can turn it off by running ``disable`` on our VM:

.. code-block:: bash

    $ sudo pro disable cis


Let's now run ``pro status`` to see what happened to ``cis``:

.. code-block:: text

    SERVICE          ENTITLED  STATUS    DESCRIPTION
    cc-eal           yes       disabled  Common Criteria EAL2 Provisioning Packages
    cis              yes       disabled  Security compliance and audit tools
    esm-apps         yes       enabled   Expanded Security Maintenance for Applications
    esm-infra        yes       enabled   Expanded Security Maintenance for Infrastructure
    fips             yes       disabled  NIST-certified core packages
    fips-updates     yes       disabled  NIST-certified core packages with priority security updates
    livepatch        yes       enabled   Canonical Livepatch service
    ros              yes       disabled  Security Updates for the Robot Operating System
    ros-updates      yes       disabled  All Updates for the Robot Operating System


Now we can see that ``cis`` status has gone back to being disabled.

.. important::

    The ``disable`` command doesn't uninstall any package that was installed by
    the service, or undo any configuration that was applied to the machine --
    it only removes the access you have to the service.


detach
------

Finally, what if you decide you no longer want this machine to be attached to
an Ubuntu Pro subscription?

To disable all of the Ubuntu Pro services and remove the subscription you
stored on your machine during ``attach``, you can use the ``detach`` command:

.. code-block:: bash

    $ sudo pro detach

Just like the ``disable`` command, ``detach`` will not uninstall any packages
that were installed by any of the services enabled through ``pro``.

Success!
========

Congratulations! You successfully ran a Multipass VM and used it to try out the
six main commands of the Ubuntu Pro Client.

If you want to continue testing the different features and functions of ``pro``,
you can run the command:

.. code-block:: bash

    $ pro help

This will provide you with a full list of all the commands available, and
details of how to use them. Feel free to play around with them in your VM and
see what else ``pro`` can do for you!

.. Instructions for closing down and deleting the VM
.. include:: ./common/shutdown-vm.txt

Next steps
----------

If you would now like to see some more advanced options to configure ``pro``,
we recommend taking a look at our
:ref:`how-to guides<how-to>`.

If you have any questions or need some help, please feel free to reach out to
the ``pro`` team on `#ubuntu-server` on `Libera IRC <pro_IRC_>`_ -- we're happy
to help! 

Alternatively, if you have a GitHub account, click on the "Give feedback"
link at the top of this page to leave us a message. We'd love to hear from you!

.. LINKS

.. include:: ../links.txt
