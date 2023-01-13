# How to enable FIPS

```{important}
[FIPS is supported on 16.04, 18.04 and 20.04 releases](https://ubuntu.com/security/certifications/docs/fips).
```

To use FIPS, one can either launch existing Ubuntu premium support images which
already have FIPS kernel and security pre-enabled on first boot at
[AWS Ubuntu Pro FIPS images](https://ubuntu.com/aws/fips),
[Azure Pro FIPS images](https://ubuntu.com/azure/fips) and GCP Pro FIPS Images.

Alternatively, you can enable FIPS using the Ubuntu Pro Client, which will
install a FIPS-certified kernel and core security-related packages such as
`openssh-server/client` and `libssl`. 

```{danger}
Disabling FIPS is not currently supported: only use it on machines intended
expressly for this purpose.
```

```{danger}
Enabling FIPS should be performed during a system maintenance window because
this operation makes changes to underlying SSL-related libraries and requires a
reboot into the FIPS-certified kernel.
```

To enable FIPS, run:

```console
$ sudo pro enable fips
```

You should see output like the following, indicating that the FIPS packages has
been installed:

```
Installing FIPS packages
FIPS enabled
A reboot is required to complete installl
```
