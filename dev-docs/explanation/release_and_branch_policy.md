# Ubuntu release and branch policy

This page explains which Ubuntu releases the `main` branch supports, which
releases live on their own maintenance branch, and how a release moves from
one to the other.

For the step-by-step release procedures for `main`, see
[Release a new version](../how-to/release_a_new_version.md) and
[Release a hotfix](../how-to/release_a_hotfix.md). For the steps to move a
release off `main`, see
[Move a Legacy Ubuntu release off `main`](../how-to/move_a_legacy_release_off_main.md).

## Which releases does `main` support?

`main` supports every Ubuntu release that is in standard support or in
Expanded Security Maintenance (ESM), plus the current development release. Get
the current list from `distro-info`, which stays current as releases change:

```bash
ubuntu-distro-info --supported
ubuntu-distro-info --supported-esm
ubuntu-distro-info --devel
```

An LTS release leaves `main` when its ESM period ends and it enters Legacy
support. From then on, the release gets updates from a maintenance branch,
described below. An interim release leaves `main` at its end of life and gets
no maintenance branch.

## What is a maintenance branch?

A maintenance branch is a long-lived branch that holds the
`ubuntu-pro-client` source for one Legacy release. It starts from the last
release of `main` that shipped to that Ubuntu release. The branch is named
after the Ubuntu release, for example `xenial`.

These maintenance branches exist in `canonical/ubuntu-pro-client` today:

| Branch | Ubuntu release | Starts from | Published to |
| --- | --- | --- | --- |
| `xenial` | 16.04 Xenial | the `37.1` tag | The Ubuntu archive |
| `19.7-trusty` | 14.04 Trusty | 19.7 | The Ubuntu archive |
| `24.2-trusty` | 14.04 Trusty | 24.2 | [`ppa:ua-client/legacy-trusty`](https://launchpad.net/~ua-client/+archive/ubuntu/legacy-trusty) |

### Why does Trusty have two branches?

Trusty is the one exception to the naming rule, because two versions of
`ubuntu-advantage-tools` are in use on Trusty:

- `19.7-trusty` holds the version in the Ubuntu archive (`19.7ubuntu0.x` in
  `trusty-security` and `trusty-updates`).
- `24.2-trusty` holds a special release for Ubuntu Pro cloud images on Trusty.
  It adds the `esm-infra-legacy` service, which those images didn't know
  about when they were built. It ships `24.2~14.04.x` through the
  `ppa:ua-client/legacy-trusty` PPA, and isn't in the Ubuntu archive.

Each branch name includes the version so the two Trusty branches can be told
apart. New maintenance branches use the release name alone.

## How do updates reach a maintenance branch?

Maintenance branches are updated only through the release's `-security`
pocket. They don't get Stable Release Updates (SRUs), so the SRU process in
[Release a new version](../how-to/release_a_new_version.md) doesn't apply to
them. The `24.2-trusty` branch is the exception again: its updates go to the
`legacy-trusty` PPA.

Maintenance branches don't get new features, new services or refactors.

## Where does Xenial stand?

Xenial entered Legacy support in April 2026 and now lives on the `xenial`
branch. It is the first release to leave `main` under this policy. Every step
in [Move a Legacy Ubuntu release off `main`](../how-to/move_a_legacy_release_off_main.md)
applies to Xenial except two, which are deferred: removing code that only
runs on Xenial, and replacing its rows in the feature tests.

### TODO: remove Xenial rows from the feature tests

The Xenial rows in `features/` stay in place for now. A maintainer will
replace them once they can be reviewed.

Until that is done:

- CI on `main` skips Xenial rows.
- New scenarios on `main` don't get Xenial rows.

### TODO: remove code that only runs on Xenial

The client, its packaging and its tests still contain code that only runs on
Xenial, such as release checks in `uaclient/`, `debian/rules` and the postinst
scripts, and the AppArmor templates. That code is dead on `main` but harmless.
A maintainer will remove it following
[Remove code that only runs on the release](../how-to/move_a_legacy_release_off_main.md#remove-code-that-only-runs-on-the-release).
