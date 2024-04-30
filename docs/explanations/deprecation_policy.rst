Ubuntu Pro Client Feature Deprecation Policy
********************************************

When pro-client introduces new features, particuarly features designed for
other software to integrate with, we assume those features become relied-upon
in all Ubuntu releases we support. That includes the oldest and also the newest
(at time of writing, the oldest is 16.04 and the newest is 24.04).  The newest
supported Ubuntu release typically has ~12 years of life left between LTS, ESM
and Legacy coverage. That means we need to support any given feature in a
backwards compatible way for at least 12 years.  This is particularly true for
any integration point with machine-readable output (e.g. our API functions, any
command with json formatted output). It is also true for important features
that, even if lacking intentional machine-usability, are likely to be used in
automation (e.g. any form of “pro attach” or “pro enable” that doesn't require
interaction).

Removing features by release
============================

We maintain the LTS promise of stability for all the LTS's we support,
therefore we cannot remove a given feature from any LTS that already has the
feature.  Instead, we will remove features starting on a devel Ubuntu release
onward. To make the transition more apparent to consumers and give them time to
adjust, we will only remove features in interim devel releases. We will not
remove a feature for the first time in an LTS devel release. When the given
feature is called on a release where it has been removed, pro-client will
return an error code and message describing what to do instead of using the
removed feature.

This “per-release-removal” will be implemented with simple checks in the
python, e.g. “if is_before(current_release, “24.10”): feature else: error”.

Features will only be per-release-removed once a better replacement is
available on all supported Ubuntu releases via SRU. The soonest allowed
per-release-removal is the next new interim release after the replacement is
SRU'd to all Ubuntu releases. Note that this is the soonest allowed. Adding
additional releases that still support the feature can make it easier for
people and tools relying on the feature to support many releases and give them
time to transition to the replacement feature. If the maintenance cost of a
particular old feature is low, we will consider keeping it around longer.

Deprecation warnings on releases that keep the feature
======================================================

When a feature is removed in e.g. 24.10 onward, it will continue to exist in
all prior supported releases; however, features in pro are often expected to
work consistently across all supported ubuntu releases. Any feature we remove
should either not apply to new Ubuntu releases, or should have a better
alternative available that does work consistently across all supported Ubuntu
releases. So when we remove a feature in future releases, all releases that
still support the feature should start emitting a deprecation warning. This
warning will tell the user that this feature will not work on future Ubuntu
releases, and point them to the alternative.

Eventual total removal
======================

Once a feature is “per-release-removed” on all currently supported releases,
then we can actually delete the feature and connected code from the pro-client.
For example, if we remove a given feature in 24.10, then we will be able to
delete the code in ~2036 when 24.04 noble legacy support ends.

Documentation
=============

For features that are removed per-release, we will add notices to the related
documentation noting which Ubuntu releases they are supported on, and also
directing the reader to the replacement.
