---
name: ubuntu-releases
description: 'Classify an Ubuntu release and look up its lifecycle using distro-info. Use whenever you see or are told about an Ubuntu release (version number, series, or full name) and need to know whether it is in development, supported, ESM-only, or unsupported, whether it is LTS, or when it was released or reaches end of life.'
---

# Ubuntu Releases

Query `ubuntu-distro-info` rather than relying on remembered lifecycle dates. A new release ships every six months, so remembered status goes stale. Get all release data from `ubuntu-distro-info` commands. Don't read its data files directly.

## Identify the series

`--series` accepts only the lowercase series name, such as `jammy`. To translate a version number (`22.04`) or full name (`Jammy Jellyfish`), find it in `ubuntu-distro-info --all -f`, which prints lines like `Ubuntu 22.04 LTS "Jammy Jellyfish"`. The series is the first word of the codename in lowercase.

If the release isn't in that list, or `--series` reports `unknown distribution series`, report that the installed `distro-info-data` may be stale. Don't guess a classification.

## Classify it

```sh
ubuntu-distro-info --devel
ubuntu-distro-info --supported
ubuntu-distro-info --supported-esm
```

Use the first rule that matches:

1. **Development**: equals `--devel`.
2. **Normally supported**: listed by `--supported`.
3. **ESM-only**: listed by `--supported-esm`.
4. **Unsupported**: anything else. An unsupported LTS may still be covered by the paid Legacy add-on, which `ubuntu-distro-info` doesn't report. Mention this possibility for an LTS rather than stating it as fact.

`--devel` exits 1 with `Distribution data outdated` when the installed data knows of no development series. Report that there's no known development series and that the data may be stale.

A release is LTS if `ubuntu-distro-info --series=<series> -r` contains `LTS`, such as `22.04 LTS`. `--lts` and `--stable` return only the latest LTS and latest stable release.

## Several releases

When you see several releases together, such as jammy, noble, and resolute, check whether they form a set the lists define. Compare them against `--supported -f`, `--supported-esm -f`, and `--all -f`, which show each release's version, `LTS` marker, and name. For example, if they are exactly the LTS entries in `--supported`, they are "the supported LTS releases". Name the set by its rule because the members change with each release. If they match no set, say so.

## Dates

Add `--date=YYYY-MM-DD` to any command to answer as of that date instead of today.

`--series=<series> --days=<milestone>` prints the days from today (or `--date`) to a milestone. Negative means the milestone has passed. Milestones are `created`, `release`, `eol`, `eol-server`, and `eol-esm`. It prints `(unknown)` when the milestone doesn't apply, such as `eol-esm` for a non-LTS release. For the calendar date, add the day count to the query date.

Use `-r`, `-c`, or `-f` to print the version, series, or full name.
