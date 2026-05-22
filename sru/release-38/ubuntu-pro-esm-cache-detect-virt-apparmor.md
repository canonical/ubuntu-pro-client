# AppArmor changes for `ubuntu_pro_esm_cache_detect_virt`

This fix adds the `perfmon` capability to the AppArmor profile. It also inverts the logic when adding the following rule to the `ubuntu_pro_esm_cache_systemctl` profile:

```text
    unix bind addr=@*/bus/systemctl/{,system},
```

So that Noble+ is included. Previously it was only Noble, and that meant Resolute was a regression.

## `perfmon`

This bug is hard to reproduce locally since `systemd-detect-virt` has many logical branches and fallbacks it takes depending on what it can access.

On Resolute and forward, this can be fixed by simply deferring to the existing `systemd-detect-virt` AppArmor profile. It's simpler for backporting to simply add `capability perfmon` to the existing `ubuntu_pro_esm_cache_systemd_detect_virt` profile, though.

The next release should use the existing AppArmor profile.

## `systemctl`

This bug is also tough to reproduce locally. From this point forward, the necessary AppArmor rules will be included due to the changes in the templating logic.

## Notes for SRU uploader

The CPC team has confirmed that these changes fix the bugs reported in [LP #2143251](https://bugs.launchpad.net/ubuntu/+source/ubuntu-advantage-tools/+bug/2143251).
