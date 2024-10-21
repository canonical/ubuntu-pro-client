How to display USNs that affect the system
******************************************

To display which USNs affect the system, run the command:

.. code-block:: bash

    $ pro vulnerability list --usns


When running the command you should see an output like this:

.. code-block:: text

    Ubuntu Security Notices (USN):
    VULNERABILITY  FIX AVAILABLE FROM  AFFECTED INSTALLED PACKAGES
    USN-5292-3     esm-infra           snapd
    USN-5352-1     esm-infra           libtasn1-6
    USN-5593-1     esm-infra           libzstd1
    USN-5707-1     esm-infra           libtasn1-6
    USN-5720-1     esm-infra           libzstd1

    Vulnerabilities with applied fixes:
        1 applied via Ubuntu Security

    Vulnerabilities with fixes available:
        5 fixable via Ubuntu Pro

Note that this output is similar to what we describe in 
:ref:`pro vulnerability list output <pro-vulnerability-list>`.
The main differance is that we don't have a ubuntu priority for a USN and therefore
this is not displayed in the output of the command.
