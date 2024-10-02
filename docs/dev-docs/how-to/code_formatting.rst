.. _code_formatting:

Code formatting
***************

The ``ubuntu-pro-client`` code base is formatted using
`black <https://github.com/psf/black>`_, and imports are sorted with
`isort <https://github.com/PyCQA/isort>`_.  When making changes, you
should ensure that your code is blackened and isorted, or it will
be rejected by CI.

Formatting the whole code base is as simple as running:

.. code-block:: bash

   black uaclient/
   isort uaclient/

To make it easier to avoid committing incorrectly-formatted code, this
repo includes configuration for `pre-commit <https://pre-commit.com/>`_
which will stop you from committing any code that isn't blackened. To
install the project's pre-commit hook, install ``pre-commit`` and run:

.. code-block::

   pre-commit install

(To install ``black`` and ``pre-commit`` at the appropriate versions for
the project, you should install them via ``dev-requirements.txt``)
