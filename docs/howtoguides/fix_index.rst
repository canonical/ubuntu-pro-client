.. _fix_index:

Handle vulnerabilities
**********************

Using the Pro Client, you can handle individual vulnerabilities (both CVEs and
USNs) that may be affecting your machine. You can also preview what will happen
if you run the ``pro fix`` command on a specific vulnerability, and control
is related USNs are fixed.

* :ref:`Check if a system is affected <pro-fix-check-cve>`
* :ref:`Use pro fix to resolve a CVE or USN <pro-fix-resolve-cve>`
* :ref:`Preview pro fix results <pro-fix-dry-run>`
* :ref:`Skip fixing related USNs <pro-fix-skip-related>`

You can also resolve multiple vulnerabilities at once using the API.

* :ref:`Preview result of fixing multiple CVEs <how_to_better_visualise_fixing_multiple_cves>`

.. TOC

.. toctree::
   :titlesonly:
   :hidden:

   Check if affected by a CVE <fix_how_to_know_if_system_affected_by_cve>
   Use pro fix to resolve a CVE/USN <fix_how_to_resolve_given_cve>
   Preview pro fix results <fix_how_to_know_what_the_fix_command_would_change>
   Skip fixing related USNs <fix_how_to_not_fix_related_usns>
   Preview result of fixing multiple CVEs <fix_how_to_better_visualise_fixing_multiple_cves>

