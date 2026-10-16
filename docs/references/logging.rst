.. _logging_reference:

Logging schema
**************

``pro`` writes one JSON array per log record:

.. code-block:: text

   ["2026-10-15T18:42:57.906", "DEBUG", "ubuntupro.cli", "main", 287, "Executed with sys.argv: ['/usr/bin/pro', 'api', 'u.pro.status.is_attached.v1']", {}]

.. list-table::
   :header-rows: 1

   * - Position
     - Field
     - Description
   * - 0
     - Timestamp
     - Local time, in the format ``YYYY-MM-DDTHH:MM:SS.mmm``
   * - 1
     - Level
     - ``DEBUG``, ``INFO``, ``WARNING``, ``ERROR``, or ``CRITICAL``
   * - 2
     - Logger
     - The ``pro`` module that wrote the record, for example
       ``ubuntupro.cli``
   * - 3
     - Function
     - The function that wrote the record
   * - 4
     - Line
     - The source line that wrote the record
   * - 5
     - Message
     - The log message
   * - 6
     - Extra
     - A JSON object. It contains ``exc_info`` when the record includes an
       exception, ``stack_info`` when it includes a stack trace, and any other
       fields that the caller adds
