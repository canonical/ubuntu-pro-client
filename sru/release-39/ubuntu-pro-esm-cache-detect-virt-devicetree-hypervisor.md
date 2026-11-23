# AppArmor: allow `systemd-detect-virt` to read the devicetree hypervisor node on jammy

On jammy ppc64el, `systemd-detect-virt` run by the ESM cache update is confined by `ubuntu_pro_esm_cache_systemd_detect_virt`. The profile did not allow reading `/sys/firmware/devicetree/base/hypervisor/compatible`, so AppArmor logged:

```text
apparmor="DENIED" operation="open" profile="ubuntu_pro_esm_cache_systemd_detect_virt" name="/sys/firmware/devicetree/base/hypervisor/compatible" comm="systemd-detect-" requested_mask="r" denied_mask="r"
```

This fix adds a read rule for that path to the profile, rendered only for jammy (see `debian/apparmor/ubuntu_pro_esm_cache.jinja2`). It is a file read, not a capability denial, so it does not re-apply the reverted `perfmon` change for jammy.

Reported in [LP #2156929](https://bugs.launchpad.net/ubuntu/+source/ubuntu-advantage-tools/+bug/2156929). Tracked in UPRO-1339.

## Notes for SRU uploader

The denial only occurs on ppc64el, which we do not test ourselves. CPC must reproduce and confirm the fix with a test build.

Launch a jammy ppc64el VM, SSH in and run:

```sh
# Confirm no logs
journalctl --no-pager | grep 'apparmor="DENIED"' | grep 'ubuntu_pro_esm_cache'

# Attach to Pro:
sudo pro attach <token> --no-auto-enable

# Action which triggers denied logs
sudo apt update

# Confirm logs now present (before the fix)
journalctl --no-pager | grep 'apparmor="DENIED"' | grep 'ubuntu_pro_esm_cache'
```

Install the new package and confirm the fix:

```sh
# Clear existing logs
sudo journalctl --rotate
sudo journalctl --vacuum-time=1s

# Confirm no logs
journalctl --no-pager | grep 'apparmor="DENIED"' | grep 'ubuntu_pro_esm_cache'

# Install test package
sudo dpkg -i <test.deb>

# Action which triggers denied logs
sudo apt update

# Confirm still no logs
journalctl --no-pager | grep 'apparmor="DENIED"' | grep 'ubuntu_pro_esm_cache'
```

CPC confirmation: _pending_
