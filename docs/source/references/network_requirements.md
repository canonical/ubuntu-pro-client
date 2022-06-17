# UA Network Requirements

Using the UA client to enable support services will rely on network access to obtain updated service
credentials, add APT repositories to install deb packages and install [snap packages](https://snapcraft.io/about) when
Livepatch is enabled. Also see the Proxy Configuration explanation to inform UA client of HTTP(S)/APT proxies.

Ensure the managed system has access to the following port:urls if in a network-limited environment:

* 443:https://contracts.canonical.com/ - HTTP PUTs, GETs and POSTs for UAClient interaction
* 443:https://esm.ubuntu.com/\* - APT repository access for most services

Enabling kernel Livepatch require additional network egress:

* snap endpoints required in order to install and run snaps as defined in [snap forum network-requirements post](https://forum.snapcraft.io/t/network-requirements/5147)
* 443:api.snapcraft.io
* 443:dashboard.snapcraft.io
* 443:login.ubuntu.com
* 443:\*.snapcraftcontent.com - Download CDNs
