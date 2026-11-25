# AppArmor: allow python3 to read `/proc/sysinfo` in `ubuntu_pro_esm_cache` on jammy, noble and resolute

On s390x, the `python3` process confined by `ubuntu_pro_esm_cache` (run by the ESM cache update) opens `/proc/sysinfo`. The profile did not allow it, so AppArmor logged:

```text
apparmor="DENIED" operation="open" profile="ubuntu_pro_esm_cache" name="/proc/sysinfo" comm="python3" requested_mask="r" denied_mask="r"
```

`systemd-detect-virt` is run under its own child profile (`ubuntu_pro_esm_cache_systemd_detect_virt`), which does not inherit the parent's rules, and it reads `/proc/sysinfo` as well:

```text
apparmor="DENIED" operation="open" profile="ubuntu_pro_esm_cache_systemd_detect_virt" name="/proc/sysinfo" comm="systemd-detect-" requested_mask="r" denied_mask="r"
```

This fix adds a read rule for `@{PROC}/sysinfo` to both the `ubuntu_pro_esm_cache` profile and the `ubuntu_pro_esm_cache_systemd_detect_virt` child profile, rendered only for jammy, noble and resolute (see `debian/apparmor/ubuntu_pro_esm_cache.jinja2`).

Reported in [LP #2156933](https://bugs.launchpad.net/ubuntu/+source/ubuntu-advantage-tools/+bug/2156933).

## Notes for SRU uploader

The denial only occurs on s390x, which we do not test ourselves. CPC must reproduce and confirm the fix with a test build.

Launch a jammy, noble or resolute s390x VM and SSH in. The denial is logged by the kernel when `esm-cache.service` runs. `sudo apt update` starts that unit in the background (`--no-block`), so wait for it to finish before checking the logs.

### Reproduce the denial (before the fix)

```sh
# Record the start time so older log entries are ignored
START="$(date '+%Y-%m-%d %H:%M:%S')"

# Action which triggers denied logs
sudo apt update
sleep 10

# Expect a DENIED line for /proc/sysinfo
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

CPC confirmation: _pending_
