---
name: ubuntu-releases
description: 'Classify an Ubuntu release and look up its lifecycle using distro-info. Use whenever you see or are told about an Ubuntu release (version number, series, or full name) and need to know whether it is in development, supported, ESM-only, legacy, or unsupported, whether it is LTS, or when it was released or reaches end of life.'
---

# Ubuntu Releases

Get all release data from `ubuntu-distro-info`, not from memory. A new release ships every six months, so remembered status goes stale.

`--series` accepts only the lowercase series name. To map a version number or full name to a series, use `ubuntu-distro-info --all -f`.

If the release is unknown or the tool reports outdated data, report that the installed `distro-info-data` may be stale. Don't guess a classification.

## Classify it

Use the first rule that matches:

1. **Development**: equals `--devel`.
2. **Normally supported**: listed by `--supported`.
3. **ESM-only**: listed by `--supported-esm`.
4. **Legacy**: an LTS whose ESM ended (`--days=eol-esm` is negative) less than five years ago. The paid Legacy add-on extends coverage five years past ESM. `ubuntu-distro-info` doesn't report this, so derive it.
5. **Unsupported**: anything else.

## Several releases

When you see several releases together, such as jammy, noble, and resolute, check whether they form a set the lists define, such as "the supported LTS releases". Name the set by its rule, because the members change with each release. If they match no set, say so.
