.. _pro-check-list-cves:

How to know if a system is affected by this list of CVEs?
*********************************************************

.. include:: ../includes/pro-fix-intro.txt

If you have a list of `Common Vulnerabilities and Exposure <cve_>`_ (CVEs) and `Ubuntu Security Notice <usn_>`_ (USNs) and want to check if your Ubuntu system is affected by it, you can check using the ``u.pro.security.fix.cve.plan.v1`` API endpoint as we'll show you in this guide.

.. note::
    The ``u.pro.security.fix.cve.plan`` API is provided as a part of the Ubuntu Pro Client (``pro``), which is a security tool for Ubuntu systems. The Ubuntu Pro Client comes pre-installed on every Ubuntu system. You can run ``pro help`` in your terminal window to see a list of the ``pro`` services and commands available.

Using the ``pro.fix.cve.plan`` API
----------------------------------

To check if your system is affected by a list of CVEs, you need to use the ``u.pro.security.fix.cve.plan.v1`` API endpoint since the
``pro fix --dry-run`` CLI command is only used to check individual CVEs. This endpoint will output a JSON blob containing the current status of each CVE, as can be seen :ref:`in the endpoint documentation <cve-execute-api-v1>`.

To better visualise the current status of each CVE from the JSON output we can use a ``jq`` filter.
The ``jq`` command can parse JSON data directly in the terminal, creating a more readable output. To learn more about it, refer to `the jq manpage <https://manpages.ubuntu.com/manpages/man1/jq.1.html>`_

First, we need to install ``jq`` by running the following command:

.. code-block:: bash

    sudo apt update & sudo apt install jq -y

Once ``jq`` is installed, we can parse the JSON data returned from the plan API.

For example, if we want to see if our system is affected by the following CVEs: **CVE-2020-28196, CVE-2020-15180**
and **CVE-2017-9233**.

We make use of the plan API by running the following command:

.. code-block:: bash

    pro api u.pro.security.fix.cve.plan.v1 --data '{"cves": ["CVE-2020-28196", "CVE-2020-15180", "CVE-2017-9233"]}' \ 
        | jq -r '.data.attributes.cves_data.cves[] | "\(.title) (\(.description)) - Current Status: \(.current_status)"'

This command will return an output that will have the following structure:

.. code-block:: bash

    CVE-2020-28196 (Kerberos vulnerability) - Current Status: not-affected
    CVE-2020-15180 (MariaDB vulnerabilities) - Current Status: not-affected
    CVE-2017-9233 (Coin3D vulnerability) - Current Status: not-affected

Note that each entry in this output consists of three fields:

* **CVE NAME**: The name of the CVE
* **CVE DESCRIPTION**: The description of the CVE
* **CVE STATUS**: The current status of the CVE

.. LINKS
.. include:: ../links.txt
