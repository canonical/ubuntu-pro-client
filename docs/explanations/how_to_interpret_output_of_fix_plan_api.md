# How to interpret the output of the fix plan API endpoint

In the Pro Client version 29, we introduce two distinct endpoints:

* `u.pro.security.fix.cve.plan.v1`
* `u.pro.security.fix.usn.plan.v1`

These endpoints can be used to verify the needed steps for fixing a list of [CVEs/USNs](cves_and_usns_explained.md).
When using the CVE endpoint, the expected output is as follows:

```json
{
  "_schema_version": "v1",
  "data": {
    "attributes": {
      "cves_data": {
        "cves": [
          {
            "error": null,
            "expected_status": "EXPECTED_STATUS",
            "plan": [
              {
                "data": {
                  "binary_packages": [
                    "package"
                  ],
                  "source_packages": [
                    "package"
                  ]
                },
                "operation": "apt-upgrade",
                "order": 1
              }
            ],
            "title": "CVE-2017-9233",
            "warnings": []
          }
        ],
        "expected_status": "EXPECTED_STATUS"
      }
    },
    "meta": {
      "environment_vars": []
    },
    "type": "CVEFixPlan"
  },
  "errors": [],
  "result": "success",
  "version": "29",
  "warnings": []
}
``` 

From this output, we can see that the **cves_data** object contains two attributes:

* **cves**: A list of CVE objects containing the plan for fixing each of them.
* **expected_status**: The expected status of the fix operation considering **all** CVEs.
                       This means that if one CVE cannot be fixed, this field will reflect that.


If we take a look at a CVE object, we will see the following structure:

* **title**: The title of the CVE.
* **error**: Any error captured when creating the CVE plan will appear here. The error object
             will be detailed in a following section.
* **expected_status**: The expected status of the CVE if the plan was to be executed. There are
  three possible scenarios: **fixed**, **still-affected** and **not-affected**.
  The system is considered **still-affected** if there is something that
  prevents any required packages from being upgraded. The system
  is considered **not-affected** if the CVE doesn't affect the system at all.
* **plan**: The plan that would need to be executed to fix the CVE. We will detail each
  possible plan step in a following section.
* **warnings**: Warnings that can happen when generating the plan. For example, if the CVE doesn't
  have a fix available for a given package, this will be reflected here. We will detail the possible
  warnings in a following section.


## What operations can appear in the plan array?

The plan array details all of the necessary operations that need to take place
to fix the CVE. Note that there are some situations where a CVE cannot be fully fixed. If that
happens, the **warnings** fields will be populated with objects describing what prevents
the CVE from fully being fixed.

Since the plan array is composed of operations, it is important to understand
each one of them. There are four distinct operations that can appear in the plan array, they are:

### APT Upgrade

This operation details which package (or packages) would need to be upgraded to fix the CVE.
The JSON representation for this step is:

```json
{
  "data": {
    "binary_packages": ["binary_package"],
    "source_packages": ["source_package"]
  },
  "operation": "apt-upgrade",
  "order": 1
}
``` 

This step provides all the binary and source packages that need to be upgraded through the `data` object.

### Attach

This operation informs that the user will need to attach to a Pro subscription.
The JSON representation for this step is:

```json
{
  "data": {
    "reason": "required-pro-service"
  },
  "operation": "attach",
  "order": 1
}
```

The `reason` field details why an attach is needed. This can be either because the user has
an expired subscription or the fix requires a specific Pro service to upgrade an affected
package.

### Enable

This operation details that the user needs to enable a specific Pro service.
The JSON representation for this step is:

```json
{
  "data": {
    "service": "esm-infra"
  },
  "operation": "enable",
  "order": 1
}
```

The `data` object contains the name of the service that needs to be enabled.

### NoOp

This indicates that no operations need to be performed to address the CVE.
The JSON representation for this step is:

```json
{
  "data": {
    "status": "system-not-affected"
  },
  "operation": "no-op",
  "order": 1
}
```
  
The `data` object will state why no operation is needed. This can either be because the CVE doesn't
affect the system, or because the CVE is already fixed in the machine.

## What warnings can be generated?

There are two distinct warnings that can happen when executing the plan API:

### Package cannot be installed

This happens when the endpoint identifies that a given package
cannot be installed (i.e. the user lacks a required APT source in the machine). This can be seen
in the following JSON representation:

```json
{
  "data": {
    "binary_package": "binary_package",
    "binary_package_version": "3.5.12-1ubuntu7.16",
    "source_package": "source_package"
  },
  "order": 1,
  "warning_type": "package-cannot-be-installed"
}
```

The `data` object details the package that cannot be installed and the package version.

### Security issue not fixed

This happens when the CVE doesn't provide a fix for some of the
affected packages. This can be seen in the following JSON representation:

```json
{
  "data": {
    "source_packages": ["source_package"],
    "status": "needs-triage"
  },
  "order": 1,
  "warning_type": "security-issue-not-fixed"
}
```

## What errors can be generated?

There are two errors that can occur when running this API endpoint. Those errors happen either
when a CVE has an invalid format, or if it doesn't exist. When an error happens, it will
be described by the following JSON representation:

```json
{
  "code": "security-fix-not-found-issue", 
  "msg": "Error: CVE-XXXX-XXXXX not found."
}
```


## Why do we need the order attribute?

The order attribute is used to help the user to properly understand the exact sequence of events
that will happen when the fix is performed. This is particularly true for situations where
we have warnings that are held outside the plan object.


## What about the USN endpoint?

The structure, as described for CVEs, works in exactly the same way for a USN. The only difference for the USN
endpoint is how the USN object is represented. This can be seen here:

```json
{
  "usns": [
    {
      "related_usns_plan": [],
      "target_usn_plan": {}
    }
  ]
}
```

We can see that there is a distinction between the **target** USN and the **related** USNs.
To better understand that distinction, please refer to
[our explanation of CVEs and USNs](cves_and_usns_explained.md).
