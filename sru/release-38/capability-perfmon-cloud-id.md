# Add capability `perfmon` to `cloud_id`

This bug is hard to reproduce locally since it only detectable on Azure VMs.

## Notes for SRU

This only adds a capability; releases that didn't need this capability won't be affected. Releases that didn't define this capability are explicitly excluded using the templating.

The CPC team has confirmed that the addition of this capability fixes their issue and has provided reproduction steps:

Reproduce using canonical:ubuntu-24_04-lts:server:latest image on Azure

Confirm there no are no denials present initially:

```sh
journalctl --no-pager | grep 'apparmor="DENIED"' | grep 'cloud_id'
sudo apt update
journalctl --no-pager | grep 'apparmor="DENIED"' | grep 'cloud_id'
```

Attach to Pro:

```sh
sudo ua attach <token> --no-auto-enable
```

Confirm that denials appear after attaching:

```sh
sudo apt update
journalctl --no-pager | grep 'apparmor="DENIED"' | grep 'cloud_id'
```
