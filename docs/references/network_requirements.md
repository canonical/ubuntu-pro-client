# Ubuntu Pro Client network requirements

Using the Ubuntu Pro Client to enable support services will rely on network
access to:

- Obtain updated service credentials
- Add APT repositories to install `deb` packages
- Install [`snap` packages](https://snapcraft.io/about) when Livepatch is
  enabled.

```{seealso}

You can also refer to our [Proxy Configuration guide](../howtoguides/configure_proxies.md)
to learn how to inform Ubuntu Pro Client of HTTP(S)/APT proxies.
```

## Network-limited

Ensure the managed system has access to the following port:urls if in a
network-limited environment:

* `443:https://contracts.canonical.com/`: HTTP PUTs, GETs and POSTs for Ubuntu
  Pro Client interaction.
* `443:https://esm.ubuntu.com/\*`: APT repository access for most services.

## Enable kernel Livepatch

Enabling kernel Livepatch requires additional network egress:

* `snap` endpoints required in order to install and run snaps as defined in
  [snap forum network-requirements post](https://forum.snapcraft.io/t/network-requirements/5147)
* `443:api.snapcraft.io`
* `443:dashboard.snapcraft.io`
* `443:login.ubuntu.com`
* `443:\*.snapcraftcontent.com` - Download CDNs
