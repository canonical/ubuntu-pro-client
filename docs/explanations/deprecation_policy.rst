.. _deprecation-policy:

Ubuntu Pro Client feature deprecation policy
********************************************

When the Pro Client introduces new features, particularly features designed for
other software to integrate with, we assume those features become relied-upon
in all Ubuntu releases we support. That includes the oldest and also the newest
(at time of writing, the oldest is 16.04 and the newest is 24.04). The newest
supported Ubuntu release typically has ~12 years of life left between LTS, ESM
and Legacy coverage. That means we need to support any given feature in a
backwards compatible-way for at least 12 years. This is particularly true for
any integration point with machine-readable output (e.g. our API functions, any
command with JSON-formatted output). It is also true for important features
that, even if lacking intentional machine-usability, are likely to be used in
automation (e.g. any form of ``pro attach`` or ``pro enable`` that doesn't require
interaction).

Removing features by release
============================

We maintain the LTS promise of stability for every supported LTS. Therefore,
we cannot remove a given feature from any LTS that already has the
feature. Instead, we will remove features starting on a `devel`_ Ubuntu release
onward. To make the transition more apparent to users and give them time to
adjust, we will only remove features in interim devel releases. We will not
remove a feature for the first time in an LTS devel release. When the given
feature is invoked on a release where it has been removed, the Pro Client will
return an error code and message describing what to do instead of using the
removed feature.

Features will only be per-release-removed once a better replacement is
available on all supported Ubuntu releases via `Stable Release Update`_ (SRU).
The soonest allowed per-release-removal is the next new interim release after
the replacement is SRU'd to all Ubuntu releases.

Deprecation warnings on releases that keep the feature
======================================================

When a feature is removed in e.g. 24.10 onward, it will continue to exist in
all prior supported releases; however, features in ``pro`` are often expected to
work consistently across all supported Ubuntu releases. Any feature we remove
should either not apply to new Ubuntu releases, or should have a better
alternative available that does work consistently across all supported Ubuntu
releases. So when we remove a feature in future releases, all releases that
still support the feature should start showing a deprecation warning. This
warning will tell the user that this feature will not work on future Ubuntu
releases, and point them to the alternative.

Documentation
=============

For features that are removed per-release, we will add notices to the related
documentation noting which Ubuntu releases they are supported on, and also
directing the reader to the replacement.

.. LINKS

.. _Stable Release Update: https://wiki.ubuntu.com/StableReleaseUpdates
.. _devel: https://canonical-ubuntu-packaging-guide.readthedocs-hosted.com/en/latest/reference/glossary/#term-Devel
