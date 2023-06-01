# About ESM, esm-apps and esm-infra

## Expanded Security Maintenance (ESM)
In the earlier version of Ubuntu Pro, when security fixes were only guaranteed
for packages in the 'main' repository, ESM used to be known as *Extended
Security Maintenance*. At that time, it referred to the additional five years
of security coverage that Pro provided after the standard five years' of
security coverage expired. It *extended* the security coverage to ten years.
This has since become known as `esm-infra` (more on that below!).

Since then, Pro has grown considerably in the size and scope of what it
provides. Where we originally only guaranteed security maintenance for
packages in the 'main' repository, we have now *expanded* the scope of our
security fixes to also include packages in the 'universe' repository. So, when
Pro went into General Availability in early 2023 and became available to all,
ESM became *Expanded Security Maintenance* to reflect the expanded scope of
our coverage. 

## What are 'main' and 'universe'?

There are tens of thousands of Ubuntu packages, all organised into sets in
*repositories*.

'*Main*' is the set of packages we identified as our focus when we launched
Ubuntu - they are packages that are either installed on every machine, or very
widely used for all kinds of deployments, from desktop to cloud. When we
launched Ubuntu LTS, we made a commitment to security-support these packages
and their dependencies in 'main' for five years, free of charge. There were
initially about 1,000 packages in 'main', and today that number has grown to
about 2,300 per Ubuntu release.

The '*universe*' repository holds all of the other open source packages in
Ubuntu; from Debian and the Ubuntu community. 'Universe' is a much bigger
repository, with over 23,000 packages per release. Historically those packages
came with no security maintenance commitment from Canonical. Nevertheless,
Canonical and the Ubuntu community provided best-effort maintenance for those
packages. With the launch of Ubuntu Pro, all of the packages of Ubuntu
'universe' get the same security maintenance commitment from Canonical as
packages in Ubuntu 'main'.

## What are `esm-infra` and `esm-apps`?

There are two streams of broad-based security updates for packages; we label
these '*apps*' (for applications) and '*infra*' (for infrastructure).

The `esm-apps` stream covers all 'universe' packages for ten years from the
release of the LTS. 

The `esm-infra` stream covers 'main' packages for the period after the
standard five year security maintenance of 'main' packages ends. We call this
'infra' because it is commonly used to build our private cloud, storage and
Kubernetes clusters, where 'universe' packages are not typically deployed. 

Commercial and enterprise customers can get a lower-cost Ubuntu Pro
(infra-only) subscription only the 'infra' components are needed, which equates
to our original ESM offering.

## How can I enable `esm-infra` and `esm-apps`?

You can manage `esm-infra` and `esm-apps` using `pro` on the command line. To
find out how, read our guide on
[enabling and disabling these services](../howtoguides/enable_esm_infra.md)
on your machine.
