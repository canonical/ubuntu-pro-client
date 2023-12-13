Using Ubuntu Pro airgapped
**************************

Airgapping (or air gapping) is a security measure that involves isolating a
machine or network from external/unsecured networks to protect sensitive data.

The term "air gapping" is often used to mean one of two things:

* **"True" airgapped**
  This describes a system operating fully offline or “internetless”. These
  systems are completely self-contained. Ubuntu Pro can still be used in a fully
  offline environment via an airgapped contract server and local mirrors. This
  allows Ubuntu Pro tokens to be distributed across the isolated network, and
  provides the security support and other benefits of Pro even without internet
  access.
  
* **Firewalled deployment**
  Although not *truly* airgapped, this refers to systems where network
  connectivity is heavily limited. On-prem setups tend to fall under this
  method, for example, with Livepatch On-prem -- where updates are fetched from
  the Canonical servers to a local machine. This provides more control over
  when, how, and which updates are deployed. 

How do I sync Pro packages in an airgapped system?
==================================================

No matter whether you are running a truly airgapped (offline) system, or one
that is heavily firewalled, running Ubuntu Pro airgapped is an advanced
use-case. The steps to achieve this are detailed in this
`guide on our support portal`_. However, it is important to note that you will
need to have a paid subscription to Ubuntu Pro.

What tools will I need?
=======================

Updating Ubuntu systems in a truly offline environment requires mirroring
Ubuntu repositories. Since Ubuntu packages can be consumed via deb packages
and/or snaps, the tool needed to mirror Ubuntu repositories depends on where
you source your packages from.

Mirror deb repositories with Landscape
--------------------------------------

Landscape is a management tool that can host a mirror of Ubuntu deb
repositories. It can be used in both kinds of airgapped environments.

In future release cycles, Landscape will also include specific features to
support airgapped use-cases. You can keep up to date with these developments in
the `Landscape Beta Discourse`_.

Mirror snaps with Snap store proxy
----------------------------------

The Snap store proxy is the equivalent tool for hosting the snap packages that
your organisation is consuming.

`Snap-store-proxy`_ is a snap that provides an edge proxy to the Snap store, so
that after your device has been registered with the proxy, all communications
with the Snap store will be sent via the proxy. This is part of the "firewalled"
deployment. Although online mode is the default for the Snap Store Proxy, it
can also `operate in offline mode`_, for true airgapped deployments.
 
Security patching with Livepatch on-prem
========================================

Livepatch is the tool that provides patching for critical and high security
vulnerabilities in the Ubuntu kernel. It can also be used in a firewalled
setup using Livepatch on-prem.

`Livepatch on-prem`_ creates a local deployment of the Canonical Livepatch
server, which retrieves patch updates from Canonical. This provides you with
greater control over when those patches roll out across your infrastructure. 

.. _Customer Support teams: https://ubuntu.com/support
.. _Landscape Beta Discourse: https://discourse.ubuntu.com/c/landscape/landscape-beta/115
.. _Snap-store-proxy: https://snapcraft.io/snap-store-proxy
.. _Livepatch on-prem: https://ubuntu.com/security/livepatch/docs/livepatch_on_prem
.. _operate in offline mode: https://docs.ubuntu.com/snap-store-proxy/en/airgap
.. _guide on our knowledge base: https://support-portal.canonical.com/knowledge-base/Get-Started-With-Ubuntu-Pro-in-an-Airgapped-Environment