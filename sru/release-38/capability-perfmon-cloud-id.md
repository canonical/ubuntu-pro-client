# Add capability `perfmon` to `cloud_id`

This bug is hard to reproduce locally since it only detectable on Azure VMs.

## Notes for SRU

This only adds a capability; releases that didn't need this capability won't be affected. Releases that didn't define this capability are explicitly excluded using the templating.

TODO: get confirmation from CPC team that bug is addressed. Use that as evidence; we'll have to trust them if we can't repro in our environments.
