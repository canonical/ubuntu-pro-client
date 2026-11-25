# AppArmor: allow `systemd-detect-virt` to read the devicetree hypervisor node

On jammy ppc64el, `systemd-detect-virt` run by the ESM cache update is confined by `ubuntu_pro_esm_cache_systemd_detect_virt`. The profile did not allow reading `/sys/firmware/devicetree/base/hypervisor/compatible`, so AppArmor logged:

```text
apparmor="DENIED" operation="open" profile="ubuntu_pro_esm_cache_systemd_detect_virt" name="/sys/firmware/devicetree/base/hypervisor/compatible" comm="systemd-detect-" requested_mask="r" denied_mask="r"
```

This fix adds a read rule for that path to the profile, rendered for all releases, as advised by the AppArmor team (see `debian/apparmor/ubuntu_pro_esm_cache.jinja2`). It is a file read, not a capability denial, so it does not re-apply the reverted `perfmon` change for jammy.

Reported in [LP #2156929](https://bugs.launchpad.net/ubuntu/+source/ubuntu-advantage-tools/+bug/2156929).

## Notes for SRU uploader

The denial only occurs on ppc64el, which we do not test ourselves. The CPC team reproduced the denial and confirmed with a test build that this change fixes the bug reported in [LP #2156929](https://bugs.launchpad.net/ubuntu/+source/ubuntu-advantage-tools/+bug/2156929).

Launch a jammy ppc64el VM and SSH in. The denial is logged by the kernel when `esm-cache.service` runs `systemd-detect-virt`. `sudo apt update` starts that unit in the background (`--no-block`), so wait for it to finish before checking the logs.

### Reproduce the denial (before the fix)

```sh
# Record the start time so older log entries are ignored
START="$(date '+%Y-%m-%d %H:%M:%S')"

# Action which triggers denied logs
sudo apt update
sleep 10

# Expect a DENIED line for the devicetree hypervisor path
journalctl -k --no-pager --since "$START" | grep 'apparmor="DENIED"' | grep 'ubuntu_pro_esm_cache'
```

### Confirm the fix

```sh
# Install test package (this also reloads the AppArmor profile)
sudo dpkg -i <test.deb>

# Confirm the profile is loaded
sudo aa-status | grep ubuntu_pro_esm_cache

# Record a new start time
START="$(date '+%Y-%m-%d %H:%M:%S')"

# Action which triggered denied logs before the fix
sudo apt update
sleep 10

# Expect no output
journalctl -k --no-pager --since "$START" | grep 'apparmor="DENIED"' | grep 'ubuntu_pro_esm_cache'
```

CPC confirmation: confirmed.
