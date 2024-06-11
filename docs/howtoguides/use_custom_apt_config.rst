How to use custom APT configuration
***********************************

The Pro Client CLI is able, through the security-status command, to show
information about installed packages in the system, their origins, and
potential updates that may be available for them. This information is also
available through the
:ref:`packages updates API<references/api:u.pro.packages.updates.v1>` and the
:ref:`packages summary API<references/api:u.pro.packages.summary.v1>` calls,
for example.

The information presented on the outputs mentioned above is taken directly
from the local APT caches. Packages, origins, versions, and candidates are all
calculated using the ``python3-apt`` library, which in turn relies on the
knowledge APT has about in a particular machine.

You may need to configure APT to have some specific behaviour. An example could
be to pass custom ``.list`` or ``.sources`` files to APT, whether to limit or
to increase knowledge about different package sources.

The Pro Client will respect the `configuration set directly on APT`_, at
execution time. If system level configuration is present, it will be used by
default. To configure APT without changing the system, there is the option of
passing the config file as an environment variable.

Use an APT config file
=========================

For example, consider that the ``/etc/apt/apt.conf.d/50-custom`` file exists,
and has this content:

.. code-block:: bash

    $ cat /etc/apt/apt.conf.d/50-custom
    # setting custom sources.list and unsetting the parts directory
    Dir::Etc::Sourcelist "/my/personal/configured/sources.list";
    Dir::Etc::Sourceparts "nonexisting-dir";

APT will use this configuration by default when running all operations.
The Pro Client will do the same - all outputs will take the custom ``.list``
file into consideration, and no ``parts`` directory will be loaded (unless the
directory set there actually exists).

Use an environment variable
===========================

Now, if the user does not want to change their system, the ``APT_CONFIG``
environment variable can be set when running APT commands, pointing to the
desired configuration file.

For example, let's say that instead of ``apt.conf.d``, the config file is
created in ``/tmp``:

.. code-block:: bash

    $ cat /tmp/custom-config
    # setting custom sources.list and unsetting the parts directory
    Dir::Etc::Sourcelist "/my/personal/configured/sources.list";
    Dir::Etc::Sourceparts "nonexisting-dir";

APT will respect this configuration if found in the aforementioned environment
variable:

.. code-block:: bash

    $ APT_CONFIG=/tmp/custom-config apt list --installed
    $ APT_CONFIG=/tmp/custom-config sudo apt update

If the variable is set when executing the Pro Client commands that depend on
APT, it will also be respected:

.. code-block:: bash

    $ APT_CONFIG=/tmp/custom-config pro security-status
    $ APT_CONFIG=/tmp/custom-config pro api u.pro.packages.updates.v1

In the python API integration
=============================

Changing the environment also works for the integration with the Pro Client's
APIs. Even after import time, it is just a matter of setting the value in
``os.environ`` before calling the function.

.. code-block:: python3

    import os
    from uaclient.api.u.pro.packages.updates.v1 import updates

    # call updates using the system APT configuration
    updates()

    # set the custom configuration, so updates will respect it, then set it
    # back to the original value so it respects the system config again
    try:
        old_env_apt_config = os.getenv("APT_CONFIG")
        os.environ["APT_CONFIG"] = "/tmp/custom-config"
        updates()
    # (...)
    finally:
        os.environ["APT_CONFIG"] = old_env_apt_config


.. _configuration set directly on APT: https://manpages.ubuntu.com/apt.conf
