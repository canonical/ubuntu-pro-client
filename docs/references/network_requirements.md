# Ubuntu Pro Client network requirements

The Ubuntu Pro Client (`pro`) and Ubuntu Pro services need to make network requests to certain services to function correctly.

```{seealso}
You can also refer to our [Proxy Configuration guide](../howtoguides/configure_proxies.md)
to learn how to inform Ubuntu Pro Client of HTTP(S)/APT proxies.
```

## Authentication
`pro` needs to authenticate with Canonical servers to provision credentials for access to the individual Ubuntu Pro services.

Necessary endpoints:
- `contracts.canonical.com:443`


## APT package based services
Many services are delivered via authenticated APT repositories. These include:
- `esm-infra` and `esm-apps`
- `fips` and `fips-updates`
- `cis` and `usg`
- `cc-eal`
- `ros` and `ros-updates`
- `realtime-kernel`

Necessary endpoints:
- `esm.ubuntu.com:443`

## Livepatch
`livepatch` requires a `snap` packaged client, so `snap`-related endpoints are necessary. The Livepatch client itself also requires network access to download the patches from the Livepatch server.
```{seealso}
The [snap documentation page](https://snapcraft.io/docs/network-requirements) may have more up-to-date information on snap-related network requirements.
```
Necessary endpoints for `snap`:
- `api.snapcraft.io:443`
- `dashboard.snapcraft.io:443`
- `login.ubuntu.com:443`
- `*.snapcraftcontent.com:443`

Necessary endpoints for `livepatch`:
- `livepatch.canonical.com:443`
