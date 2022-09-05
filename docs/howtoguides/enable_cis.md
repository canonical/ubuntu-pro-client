# How to enable CIS

> NOTE: On Focal and later releases, CIS was replaced by [USG](https://ubuntu.com/security/certifications/docs/usg),
therefore, just change `cis` to `usg` when running the enable command on those releases.

To access the CIS tooling first enable the software repository.

```console
$ sudo ua enable cis
```

You should see output like the following, indicating that the CIS package has been installed.

```
Installing CIS Audit packages
CIS Audit enabled
Visit https://security-certs.docs.ubuntu.com/en/cis to learn how to use CIS
```

Once the feature is enabled please [follow the documentation](https://ubuntu.com/security/certifications/docs/cis)
for the CIS tooling to run the provided hardening audit scripts.
