.. _how_to_better_visualise_fixing_multiple_cves:

How to better visualise the result when fixing multiple CVEs
*************************************************************

To fix multiple CVEs, you need to use the `u.pro.security.fix.cve.execute.v1` endpoint,
as the CLI `pro fix` command doesn't support multiple CVEs. However, as can be seen :ref:`in the endpoint documentation <cve-execute-api-v1>`,
this command will output a JSON blob containing the results of the fix operation for each CVE.

This doesn't allow for a quick visualisation of the fix status of each requested CVE.
To address that, we can use a `jq` filter. The `jq` command is mainly used to parse JSON data directly in
the terminal. To know more about it, please refer to `the jq manpage <https://manpages.ubuntu.com/manpages/xenial/man1/jq.1.html>`_

Before proceeding, we need to guarantee that `jq` is installed in your machine. This can be achieved
by running the following command:

.. code-block:: bash

    $ apt update & apt install jq -y

Now that `jq` is installed, we can properly parse the JSON data delivered from the execute API.
As an example, let's assume we want to fix these three CVEs: **CVE-2020-28196, CVE-2020-15180**
and **CVE-2017-9233**.

We can achieve that by running the following command:

.. code-block:: bash

    pro api u.pro.security.fix.cve.execute.v1 --data '{"cves": ["CVE-2020-28196", "CVE-2020-15180", "CVE-2017-9233"]}' \
      | jq -r '.data.attributes.cves_data.cves[] | "\(.title) (\(.description)) - \(.status)"'

We can see that the command output will be something that follows this structure here:

.. code-block:: bash

    CVE-2020-28196 (Kerberos vulnerability) - fixed
    CVE-2020-15180 (MariaDB vulnerabilities) - not-affected
    CVE-2017-9233 (Coin3D vulnerability) - fixed

Note that each entry in this output consists of three fields:

* **CVE NAME**: The name of the CVE
* **CVE DESCRIPTION**: The description of the CVE
* **CVE STATUS**: The status of the CVE which can be one of: **fixed, still-affected, not-affected**
  and **affected-until-reboot**.

If you want to change the output format, you can tweak the `jq` filter. For example, to only show
the CVE title and status, you can change the `jq` filter to:

.. code-block:: bash

    jq -r '.data.attributes.cves_data.cves[] | "\(.title) - \(.status)"'

Finally, if you want to have the same visualisation when fixing USNs, just change the `jq` filter
to:

.. code-block:: bash

    jq -r '.data.attributes.usns_data.usns[] | "\(.title) (\(.description)) - \(.status)"'
