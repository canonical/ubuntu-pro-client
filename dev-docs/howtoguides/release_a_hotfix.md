# Ubuntu Pro Client hotfix release process

For the purposes of this document, a "hotfix" is a new version of
`ubuntu-advantage-tools` to fix one specific bug that is considered urgent
enough to do outside of the normal release schedule and process.

This process is a simplified version of the [full release process](./release_a_new_version.md)
and it is recommended that you have an understanding of that process as well.

You can conceptualize this process as a "normal" SRU but with PRs on the
`ubuntu-pro-client` GitHub instead of in `git-ubuntu`.

## 1. Preparation

If there is not already a bug on Launchpad for this bug, create one.
This bug should specifically describe the bug to be fixed in the hotfix
and should follow the normal [SRU Template](https://wiki.ubuntu.com/StableReleaseUpdates#SRU_Bug_Template).

## 2. Land the fix "upstream"

Before we release the hotfix, we want to land it in the main development branch.
This is either `main` or `next-v$version` at any given time, and should always
be the "default" branch on GitHub. Landing the fix in the development branch first
ensures that it will not get left behind in the next release, which would cause a
regression.

Fix the bug and be sure to include "LP: #1234" in the commit message (replacing
"1234" with the Launchpad bug number).

Get the PR merged.

## 3. Choose the next version

Hotfixes always bump the third part of our version. Second and third parts are added as necessary.

Example table:

| Previous Version | Hotfix Version |
| ---------------- | -------------- |
| 42               | 42.0.1         |
| 42.1             | 42.1.1         |
| 42.2             | 42.2.1         |
| 42.4.1           | 42.4.2         |

The rest of this guide will refer to the previous version and hotfix version
as `$previous_version` and `$hotfix_version` respectively.

## 4. Set up the hotfix release PR

We want to release only the hotfix, so we need to base the changes on the
previous release. The previous release will be tagged `$previous_version`.

1. Checkout the previous release tag and create a branch.
   ```
   git checkout $previous_version
   git switch -c $hotfix_version-hotfix
   ```

2. Cherry pick the commit(s) that fix(es) the bug from the development branch onto this new hotfix branch.
   Resolve any conflicts as needed.

3. Add a new changelog entry for $hotfix_version. This changelog should target the current devel release of Ubuntu.
    - Be sure to include a reference to the Launchpad bug, e.g. `(LP: #1234)`

4. Update the `VERSION` variable in `uaclient/version.py` to be `"$hotfix_version"`.

5. Commit and push that branch to GitHub.

6. Create a branch from the previous release tag to use as a target for your GitHub PR.
   ```
   git checkout $previous_version
   git switch -c $previous_version-base
   ```

7. Create a PR on GitHub to merge `$previous_version-hotfix` into `$previous_version-hotfix-base`

## 5. Sponsor review, upload, and SRU review

The rest of the process is very similar to the full release process except we won't have
pre-allocated Sponsor and SRU reviewer time. Coordinate with the broader Ubuntu Server team to find
a Sponsor and SRU reviewer.

* Ask the Sponsor and SRU reviewer to review the hotfix PR on GitHub. If they request changes,
  make sure all changes make it into the development branch on GitHub in addition to the hotfix branch.
* When the Sponsor and SRU reviewer approve, create the branches for each stable release. They should be named `hotfix-$hotfix_version-$release`.
    * The only addition for each branch should be the changelog entry for the new version. The entry should be in the format
    ```
    ubuntu-advantage-tools (42.4.2~20.04) focal; urgency=medium

    * Backport new hotfix release (LP: #SRUBUG)

    -- Grant Orndorff <grant.orndorff@canonical.com>  Thu, 29 Feb 2024 09:03:11 -0500
    ```
    * The versions for the stable releases must be in the format `$hotfix_version~<release-number>`
* Tell the Sponsor that the branches are ready for them to upload to `devel` and the SRU unapproved queue.
* Check the [`-proposed` release queue](https://launchpad.net/ubuntu/xenial/+queue?queue_state=1&queue_text=ubuntu-advantage-tools) for presence of `ubuntu-advantage-tools` in unapproved state for each supported release. Note: Libera chat `#ubuntu-release` IRC channel has a bot that reports queued uploads of any package in a message like `"Unapproved: ubuntu-advantage-tools .. version"`.
* Tell the SRU Reviewer that the packages are in the `-proposed` unapproved queue. They will need to actually approve the package to move into `-proposed`.

## 6. Verification

Perform verification on the Launchpad bug using the Test Plan outlined in the description for all releases.

No additional tests need to be run unless they add value to the particular circumstances of the bug.

## 7. Finalizing the release and preparing for the next one

1. Double check that all changes in the hotfix also made it into the development branch.
2. Tag the commit that got released as `$hotfix_version`, this should be the tip of `$hotfix_version-hotfix`.
    * `git tag $hotfix_version`
    * `git push origin $hotfix_version`
3. Close the hotfix release PR and delete the `$previous_version-base` branch.
4. Perform the steps from "Releasing to our staging PPA" in the full release process but use a `~stableppaX` suffix instead of `~rcX` in the version name, and upload to `ppa:ua-client/stable` instead of staging.
