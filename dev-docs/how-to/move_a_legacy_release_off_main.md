# Move a Legacy Ubuntu release off `main`

Follow these steps when an LTS release leaves ESM and enters Legacy support.
After them, the release gets updates only from its maintenance branch, and
`main` no longer builds, tests or targets it. For why releases leave `main`
and how maintenance branches work, see the
[Ubuntu release and branch policy](../explanation/release_and_branch_policy.md).

The examples use Xenial, the release leaving `main`, and bionic, the new oldest
supported LTS. Substitute your releases.

## Before you start

Confirm the release has left ESM. A negative number means ESM has ended:

```bash
ubuntu-distro-info --series=xenial --days=eol-esm
```

## Create the maintenance branch

The branch must have the same contents as the package in the Ubuntu archive,
and it should share history with `main`. Branch from the last release commit
on `main`, then replace the tree with the archive contents.

Use `git-ubuntu` to clone the package. It imports the archive's history and
sets up a `pkg` remote with one `ubuntu/<series>-devel` branch per release.
Then add `ubuntu-pro-client` as `upstream` in that clone.

`git-ubuntu` is available as a snap:

```bash
sudo snap install --classic git-ubuntu
```

Clone the package and add the remote:

```bash
git-ubuntu clone ubuntu-advantage-tools
cd ubuntu-advantage-tools
git remote add upstream https://github.com/canonical/ubuntu-pro-client.git
git fetch upstream --tags
```

`pkg/ubuntu/<series>-devel` holds the latest package in the archive for the
release. Set the release, then look at the top entry of its
`debian/changelog`:

```bash
SERIES=xenial
git show pkg/ubuntu/$SERIES-devel:debian/changelog | head -1
```

The version is the archive version, such as `37.1ubuntu0~16.04.1`. Its
upstream part is the last version of `main` that shipped to the release, such
as `37.1`. Set variables for both:

```bash
ARCHIVE_VERSION=37.1ubuntu0~16.04.1
UPSTREAM_VERSION=37.1
```

Check that the tag resolves to a commit, and save it as `BASE`. If this
prints nothing or an error, the tag is missing or misnamed; look for it with
`git tag -l "${UPSTREAM_VERSION%%.*}*"` and by searching `debian/changelog`
history on `upstream/main`:

```bash
git rev-list -n1 $UPSTREAM_VERSION
BASE=$(git rev-list -n1 $UPSTREAM_VERSION)
```

Create the branch from that commit, and make its tree match the archive:

```bash
git switch -c $SERIES $BASE
git rm -rf --quiet .
git checkout pkg/ubuntu/$SERIES-devel -- .
git commit -m "Import $ARCHIVE_VERSION contents from the Ubuntu archive"
```

Check that the tree is identical to the archive. This must print nothing:

```bash
git diff pkg/ubuntu/$SERIES-devel $SERIES
```

Push the branch. Don't push `pkg/` history to GitHub, so use a single-parent
commit as above:

```bash
git push upstream $SERIES
```

## Remove the release from CI

In `.github/workflows/ci-integration.yaml`, remove the release from:

- the `release` list in the `package-builds` job matrix;
- the `release` list in the `integration-tests` job matrix;
- every `include` entry in the `integration-tests` job matrix with that
  `release`.

The maintenance branch keeps its own copy of the workflows, so CI there still
builds and tests the release.

## Raise the minimum Python version

`main` must support the Python version of the new oldest supported LTS. Look it
up:

```bash
rmadison -u ubuntu -s bionic python3
```

Then update the places that name the old version:

1. In `pyproject.toml`, remove the old versions from `target_version` under
   `[tool.black]`. For bionic, remove `py34` and `py35`.
2. In `AGENTS.md`, update the release and Python version in the project
   overview and in the code style rules.
3. Run `black uaclient/ features/ lib/ setup.py`. A newer target can change
   how `black` formats some code. Commit any reformatting as a separate commit.

## Remove code that only runs on the release

The client, its packaging and its tests contain code that runs only on
specific releases. Once `main` no longer ships to the release, that code is
dead on `main`. No single search finds all of it, so use the search below as
a starting point. Search for the series name and the version number:

```bash
git grep -n -i -E 'xenial|16\.04' -- . ':!debian/changelog' ':!debian/po' ':!sru/_archive' ':!features'
```

Hits can be in the Python code, the packaging scripts, the AppArmor templates
and the unit tests. Some hits aren't code, such as docs that mention the
release. Some release-specific code doesn't name the
release at all, such as workarounds for an old Python version or for old
versions of other packages, so the search doesn't find it.

For each piece of code you find, remove it if it only runs on the release, and
remove the release from lists that name it. Remove a code path only if it
can't run on any release `main` supports.

Keep code that runs on a supported release but handles the old one. Users can
still upgrade from the old release with `do-release-upgrade`, and the package
on the new release handles that upgrade. For example, when
`debian/ubuntu-advantage-tools.postinst` runs on bionic (`VERSION_ID` is
`18.04`) and `PREVIOUS_PKG_VER` contains `16.04`, it removes a systemd unit
that only Xenial packages install. Removing that code would leave the unit
behind on systems upgraded from Xenial.

The search skips `features/`. Test code there that only runs on the release
goes with the release's rows in the next step.

## Replace the release's rows in the feature tests

Each `Scenario Outline` in `features/` lists the releases it runs on in its
`Examples` table. The oldest release in the table records the oldest release
the scenario was written for, so review each table by hand.

Find the tables that use the release:

```bash
grep -rn "| xenial" features/
```

For each table:

- If the behavior applies to the new oldest supported LTS, replace the old
  release's row with a row for that release. If that release is already in
  the table, delete the old row.
- If the scenario only makes sense on the old release, delete the scenario.
