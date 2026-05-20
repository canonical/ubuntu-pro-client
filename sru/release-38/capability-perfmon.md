# Add capability `perfmon` to `ubuntu_pro_esm_cache_detect_virt`

This bug is hard to reproduce locally since `systemd-detect-virt` has many logical branches and fallbacks it takes depending on what it can access.

On Resolute and forward, this can be fixed by simply deferring to the existing `systemd-detect-virt` AppArmor profile. It's simpler for backporting to simply add `capability perfmon` to the existing `ubuntu_pro_esm_cache_systemd_detect_virt` profile, though.

The next release should use the existing AppArmor profile.

## Notes for SRU

This only adds a capability; releases that didn't need this capability won't be affected. Releases that didn't define this capability are explicitly excluded using the templating.

TODO: get confirmation from CPC team that bug is addressed. Use that as evidence; we'll have to trust them if we can't repro in our environments.
