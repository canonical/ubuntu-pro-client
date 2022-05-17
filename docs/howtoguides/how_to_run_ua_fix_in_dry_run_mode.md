# How to run fix command in dry run mode

If you are unsure on what changes will happen on your system after you run `ua fix` to address a
CVE/USN, you can use the `--dry-run` flag to see that packages will be installed in the system if
the command was actually run. For example, this is the output of running `ua fix USN-5079-2 --dry-run`:

```
WARNING: The option --dry-run is being used.
No packages will be installed when running this command.
USN-5079-2: curl vulnerabilities
Found CVEs:
https://ubuntu.com/security/CVE-2021-22946
https://ubuntu.com/security/CVE-2021-22947
1 affected source package is installed: curl
(1/1) curl:
A fix is available in UA Infra.
The machine is not attached to an Ubuntu Advantage (UA) subscription.
To proceed with the fix, a prompt would ask for a valid UA token.
{ ua attach TOKEN }
UA service: esm-infra is not enabled.
To proceed with the fix, a prompt would ask permission to automatically enable
this service.
{ ua enable esm-infra }
{ apt update && apt install --only-upgrade -y curl libcurl3-gnutls }
✔ USN-5079-2 is resolved.
```

You can see that using `--dry-run` will also indicate which actions would need to happen
to completely address the USN/CVE. Here we can see that the package fix can only be accessed
through the `esm-infra` service. Therefore, we need a UA subscription, as can be seen on this
part of the output:

```
The machine is not attached to an Ubuntu Advantage (UA) subscription.
To proceed with the fix, a prompt would ask for a valid UA token.
{ ua attach TOKEN }
```

Additionally, we also inform you that even with a subscription, we need the specific
`esm-infra` service to be enabled:

```
UA service: esm-infra is not enabled.
To proceed with the fix, a prompt would ask permission to automatically enable
this service.
{ ua enable esm-infra }
```

After performing these steps during a fix command without `--dry-run`, your machine should
no longer be affected by that USN we used as an example.
