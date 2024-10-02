.. _unit_testing:

Unit testing
************

Before proceeding with unit tests, ensure you have completed the setup
instructions in the :ref:`Getting Started tutorial <getting_started_devel>`.
This guide covers essential setup information required to run the tests.

All unit and lint tests are run using ``tox``. However, before we can run our
tests, we need to install some package dependencies. This can be achieved
through our Makefile script. To install the dependencies, first install
``make``:

.. code-block:: bash

   sudo apt install make

Then, run this command to install all the necessary dependencies:

.. code-block:: bash

   sudo make deps

After that, you can run the unit and lint tests:

.. code-block:: bash

   tox

To run only unit tests, you can specify the test environment:

.. code-block:: bash

   tox -e test

Or to run a specific test, you can specify the test file:

.. code-block:: bash

   tox -e test -- uaclient/tests/test_actions.py

.. note::
   There are a number of ``autouse`` mocks in our unit tests. These are
   intended to prevent accidental side effects on the host system from running
   the unit tests, as well as to prevent leaks of the system environment into
   the unit tests.
   One such ``autouse`` mock tells the unit tests that they are run as root
   (unless the mock is overridden for a particular test).
   These ``autouse`` mocks have helped, but may not fully prevent all side
   effects or environment leakage.

The client also includes built-in dep8 tests. These are run as follows:

.. code-block:: bash

   autopkgtest -U --shell-fail . -- lxd ubuntu:xenial

