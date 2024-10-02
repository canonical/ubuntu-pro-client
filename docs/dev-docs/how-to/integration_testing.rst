.. _integration_testing:

Integration testing
*******************

Before proceeding with the integration tests, ensure you have completed the
setup instructions in the
:ref:`Getting Started tutorial <getting_started_devel>`. This guide covers
essential setup information required to run the integration tests.

Ubuntu Pro Client `uses behave <https://behave.readthedocs.io>`_ for its
integration testing.

Test definitions
================

The integration test definitions are stored in the ``features/`` directory and
consist of two parts:

* ``.feature`` files that define the tests we want to run, and
* ``.py`` files that implement the underlying logic for those tests.

By default, integration tests will do the following on a given cloud platform:

* Launch an instance running the latest daily image of the target Ubuntu release
* Add the Ubuntu Pro Client daily build PPA: `ppa:ua-client/daily <https://code.launchpad.net/~ua-client/+archive/ubuntu/daily>`_
* Install the appropriate ``ubuntu-advantage-tools`` and ``ubuntu-advantage-pro`` debs
* Run the integration tests on the instance

The testing can be overridden to install ``ubuntu-advantage-tools`` from other
sources instead of the daily PPA by providing ``UACLIENT_BEHAVE_INSTALL_FROM``
to the behave test runner. The default is ``UACLIENT_BEHAVE_INSTALL_FROM=daily``,
and the other available options are:

- ``staging``: install from the
  `staging PPA <https://code.launchpad.net/~ua-client/+archive/ubuntu/staging>`_
- ``stable``: install from the
  `stable PPA <https://code.launchpad.net/~ua-client/+archive/ubuntu/stable>`_
- ``archive``: install the latest version available in the archive, not adding
  any PPA
- ``proposed``: install the package from the ``-proposed`` pocket -- this is
  especially useful for SRU testing (see
  :ref:`the release guide <release_a_new_version>`)
- ``custom``: install from a custom-provided PPA. If set, then two other
  variables need to be set also: ``UACLIENT_BEHAVE_CUSTOM_PPA=<PPA URL>`` and
  ``UACLIENT_BEHAVE_CUSTOM_PPA_KEYID=<signing key for the PPA>``
- ``local``: install from a local copy of the ``ubuntu-pro-client`` source code.
  This is particularly useful, as it runs the suite against the local code,
  thus including and validating the latest changes made. It is advised to run
  any related integration tests against local code changes before pushing them
  to be reviewed.

.. note::
   Note that we cache the source when running with
   ``UACLIENT_BEHAVE_INSTALL_FROM=local`` based on a hash, calculated from the
   repository state. If you change the Python code locally and run the behave
   tests against your new version, there will be new debs in the cache source
   with the new repo state hash.

Running tests
=============

To run the integration tests, use the ``tox`` command as shown below. Note that,
as shown here without arguments, this command would run all the integration
tests sequentially and would take an inordinate amount of time to complete.
Always pass arguments to this command to specify a subset of tests to run, like
this:

.. code-block:: bash

   tox -e behave

or, if you just want to run a specific file (or a test within a file):

.. code-block:: bash

   tox -e behave -- features/unattached_commands.feature
   tox -e behave -- features/unattached_commands.feature:28

or, if you want to run a specific file for a specific release and machine type,
or a specific test:

.. code-block:: bash

   tox -e behave -- features/config.feature -D releases=jammy -D machine_types=lxd-container
   tox -e behave -- features/config.feature:132 -D releases=jammy -D machine_types=lxd-vm

This will run behave tests for only the release 22.04 (Jammy Jellyfish).
Similarly, the behave tests can be run for all supported releases, including
LTS releases under ESM, and the development release at some point in the
development cycle. Note that the specific release versions will change over
time, so we recommend referring to the documentation for the latest information.

Furthermore, when developing/debugging a new scenario:

1. Add a ``@wip`` tag decorator to the scenario
2. To only run ``@wip`` scenarios, run: ``tox -e behave -- -w``
3. If you want to use a debugger:

   1. Add ``ipdb`` to ``integration-requirements.txt``
   2. Add ``ipdb.set_trace()`` in the code block you want to debug

If you're getting started with behave, we recommend at least reading through
`the behave tutorial <https://behave.readthedocs.io/en/latest/tutorial.html>`_
to get an idea of how it works and how tests are written.

Integration testing on EC2
==========================

The following ``tox`` environments allow for testing Focal on EC2:

.. code-block:: bash

   # To test ubuntu-pro-images
   tox -e behave -- -D release=focal -D machine_types=aws.pro
   # To test Canonical cloud images (non-ubuntu-pro)
   tox -e behave -- -D release=focal -D machine_types=aws.generic

To run the test for a different release, update the release version string. For
example, to run AWS Pro Xenial tests, you can run:

.. code-block:: bash

   tox -e behave -- -D release=xenial -D machine_types=aws.pro

To run EC2 tests, you will need to set up the
`pycloudlib toml file <https://github.com/canonical/pycloudlib/blob/main/pycloudlib.toml.template>`_
with the required EC2 credentials.

To specifically run non-Ubuntu Pro tests using Canonical cloud-images, an
additional token obtained from ``https://ubuntu.com/pro`` needs to be set:

.. code-block:: bash

   UACLIENT_BEHAVE_CONTRACT_TOKEN=<your_token>

To manually run EC2 integration tests with a specific AMI ID, provide the
following environment variable to launch your specific AMI instead of building
a daily ``ubuntu-advantage-tools`` image:

.. code-block:: bash

   UACLIENT_BEHAVE_REUSE_IMAGE=your-custom-ami tox -e behave -- -D release=focal -D machine_types=aws.pro


Integration testing on Azure
============================

The following ``tox`` environments allow for testing Focal on Azure:

.. code-block:: bash

   # To test ubuntu-pro-images
   tox -e behave -- -D release=focal -D machine_types=aws.pro
   # To test Canonical cloud images (non-ubuntu-pro)
   tox -e behave -- -D release=focal -D machine_types=aws.generic

To run the test for a different release, update the release version string. For
example, to run Azure Pro Xenial tests, you can run:

.. code-block:: bash

   tox -e behave -- -D machine_types=azure.pro

To run Azure tests, you will need to set up the
`pycloudlib toml file <https://github.com/canonical/pycloudlib/blob/main/pycloudlib.toml.template>`_
with the required Azure credentials.

To specifically run non-Ubuntu Pro tests using Canonical cloud-images, an
additional token obtained from ``https://ubuntu.com/pro`` needs to be set:

.. code-block:: bash

   UACLIENT_BEHAVE_CONTRACT_TOKEN=<your_token>

To manually run Azure integration tests with a specific Image ID, provide the
following environment variable to launch your specific Image ID instead of
building a daily ``ubuntu-advantage-tools`` image:

.. code-block:: bash

   UACLIENT_BEHAVE_REUSE_IMAGE=your-custom-image-id tox -e behave -- -D release=focal -D machine_types=azure.pro

Integration testing on GCP
==========================

The following ``tox`` environments allow for testing Focal on GCP:

.. code-block:: bash

   # To test ubuntu-pro-images
   tox -e behave -- -D release=focal -D machine_types=gcp.pro
   # To test Canonical cloud images (non-ubuntu-pro)
   tox -e behave -- -D release=focal -D machine_types=gcp.generic

To run the test for a different release, update the release version string. For
example, to run GCP Pro Xenial tests, you can run:

.. code-block:: bash

   tox -e behave -- -D release=xenial machine_types=gcp.pro

To run GCP tests, you will need to set up the
`pycloudlib toml file <https://github.com/canonical/pycloudlib/blob/main/pycloudlib.toml.template>`_
with the required GCP credentials.

To specifically run non-Ubuntu Pro tests using Canonical cloud-images, an
additional token obtained from ``https://ubuntu.com/pro`` needs to be set:

.. code-block:: bash

   UACLIENT_BEHAVE_CONTRACT_TOKEN=<your_token>

To manually run GCP integration tests with a specific Image ID, provide the
following environment variable to launch your specific Image ID instead of
building a daily ``ubuntu-advantage-tools`` image.

.. code-block:: bash

   UACLIENT_BEHAVE_REUSE_IMAGE=your-custom-image-id tox -e behave -- -D release=focal -D machine_types=gcp.pro

