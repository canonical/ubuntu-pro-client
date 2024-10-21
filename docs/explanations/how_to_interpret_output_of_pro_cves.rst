.. _pro-cves:

How to interpret the output of pro cves
****************************************

In the Pro Client version 35, we introduce the ``pro cves`` command.
This command will display all of installed packages that are affected
by a CVE. This can be better visualized in the following example:

.. code-block:: text

   Package         Priority     Origin        Vulnerability
   firefox         medium       esm-infra     CVE-2020-6852
   openssh         low          standard      CVE-2021-3188
   openssh         low          standard      CVE-2020-1288                                                        
   openssh         low          standard      CVE-2020-1290                                                 
   openssh-client  low          esm-apps      CVE-2021-3188
   openssh-client  low          standard      CVE-2020-1288
   openssh-client  low          standard      CVE-2020-1290
   python3-apt     medium       esm-infra     CVE-2020-6852 
   vim             critical     esm-infra     CVE-2011-3374
   vim             high         standard      CVE-2011-3380
   vim-tiny        high         -             CVE-2011-3380
   vim-tiny        low          -             CVE-2011-3380 


We can see that the table is oriented per-package. Additionally, we can see that
the table will have a line for each CVE that affects an installed package. For example,
**openssh** is affected by three distinct CVEs and because of that, it has three rows in
the table.

With that said, the table will always contain four headers:

* **Package**: The name of the package affected by a CVE
* **Priority**: The ubuntu priority for the CVE
* **Origin**: The ubuntu pocket where the fix can be found:
	* **esm-infra**: Fix is availabe on the esm-infra pocket. This means that user must have esm-infra service enabled through Pro in the machine to access it
	* **esm-apps**: Fix is availabe on the esm-apps pocket. This means that user must have esm-apps service enabled through Pro in the machine to access it
	* **fips**:     Fix is availabe on the fips pocket. This means that user must have fips service enabled through Pro in the machine to access it
	* **fips-updates**: Fix is availabe on the fips-updates pocket. This means that user must have fips-updates service enabled through Pro in the machine to access it
	* **standard**: Fix is available on the ubuntu security or updates pocket
	* **-**: No fix is available for this CVE
* **Vulnerability**: The name of the CVE

It is also important to say that the table is ordered by **Package** and **Priority**.


What if no CVEs affect the system
=================================

If no CVEs affect the system, the command will display the following message:

.. code-block:: text

	No CVES found that affect this system


Supported flags
===============

The command support two flags:

* **--unfixable**: Show only unfixable CVEs
* **--fixable**: Show only fixable CVEs
