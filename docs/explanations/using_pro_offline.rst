Using Ubuntu Pro in an offline environment
******************************************

Airgapping (or air gapping) is a security measure that involves isolating a
machine or network from external/unsecured networks to protect sensitive data.
Airgapped systems usually operate “internetless”, or with limited network
connectivity. 

Ubuntu Pro can still be used in an offline environment, via an airgapped
contract server and local mirrors. This allows Ubuntu Pro tokens to be
distributed across the isolated network, and provides the security support and
other benefits of Pro even without internet access.

How do I sync Pro packages in an airgapped system?
==================================================

This is an advanced use-case, and our `Customer Support teams`_ can help you
implement this in the best way for your specific environment. Note that this
requires a paid subscription to Ubuntu Pro.

What tools do I need?
=====================

Updating Ubuntu systems in an offline environment requires mirroring Ubuntu
repositories. Since Ubuntu packages can be consumed via deb packages and/or
snaps, the tool needed to mirror Ubuntu repositories depends on where you
source your packages from.

Mirror deb repositories with Landscape
--------------------------------------

Landscape is a management tool that can host a mirror of Ubuntu deb
repositories. 

In future release cycles, Landscape will also include features specific to
airgapped use-cases. You can keep up to date with these developments in the
`Landscape Beta Discourse`_.

Mirror snaps with Snap store proxy
----------------------------------

The Snap store proxy is the equivalent tool for hosting the snap packages that
your organisation is consuming.

`Snap-store-proxy`_ is a snap that provides an edge proxy to the Snap store, so
that after your device has been registered with the proxy, all communications
with the Snap store will be sent via the proxy.
 
Security patching
=================

Livepatch is the tool that provides patching for critical and high security
vulnerabilities in the Ubuntu kernel. It can also be used in an airgapped
setup using Livepatch on-prem, which our `Customer Support teams`_ can help you
to set up.

Livepatch on-prem
-----------------

`Livepatch on-prem`_ is a local deployment of the Canonical Livepatch server,
which retrieves patch updates from Canonical. This provides you with greater
control over when those patches roll out across your infrastructure. 


.. _Customer Support teams: https://ubuntu.com/support
.. _Landscape Beta Discourse: https://discourse.ubuntu.com/c/landscape/landscape-beta/115
.. _Snap-store-proxy: https://snapcraft.io/snap-store-proxy
.. _Livepatch on-prem: https://ubuntu.com/security/livepatch/docs/livepatch_on_prem
