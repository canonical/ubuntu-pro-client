# Ubuntu Advantage Client Releases

## Supported Ubuntu Releases

See the table under "Support Matrix for the client" in the [readme](./README.md).

## Release versioning schemes

Below are the versioning schemes used for publishing debs:

| Build target | Version Format |
| -------- | -------- |
| Devel series upstream release | `XX.YY` |
| Devel series bugfix release | `XX.YY.Z~ubuntu1`|
| Stable series release | `XX.YY~ubuntu1~18.04.1`|
| [Daily Build Recipe](https://code.launchpad.net/~canonical-server/+recipe/ua-client-daily) | `XX.YY+<revtime>-g<commitish>~ubuntu1~18.04.1` |
| Ubuntu PRO series release | binary copies of Daily PPA |
| -------- | -------- |

## Supported upgrade use-cases based on version formats

| Upgrade path | Version diffs |
| -------- | -------- |
| LTS to LTS | `20.3~ubuntu1~14.04.1 -> 20.3~ubuntu1~16.04.1` |
| LTS to Daily PPA | `20.3~ubuntu1~14.04.1 -> 20.3+202004011202~ubuntu1~14.04.1` |
| Ubuntu PRO to latest <series>-updates | `20.3+202004011202~ubuntu1~14.04.1` -> `20.4~ubuntu1~14.04.1` |
| Ubuntu PRO to Daily PPA | `20.3+202004011202~ubuntu1~14.04.1` -> `20.4+202004021202~ubuntu1~14.04.1` |

## Process


### Background

The release process for ubuntu-advantage-tools has three overarching steps/goals.

1. Release to our team infrastructure. This includes Github and the `ua-client` PPAs.
2. Release to the latest ubuntu devel release.
3. Release to the supported ubuntu past releases via [SRU](https://wiki.ubuntu.com/StableReleaseUpdates) using the [ubuntu-advantage-tools specific SRU process](https://wiki.ubuntu.com/UbuntuAdvantageToolsUpdates).

Generally speaking, these steps happen in order, but there is some overlap. Also we may backtrack if issues are found part way through the process.

An average release should take somewhere between 10 and 14 calendar days if things go smoothly, starting at the decision to release and ending at the new version being available in all supported ubuntu releases. Note that it is not 2 weeks of full time work. Most of the time is spent waiting for review or sitting in proposed.

### Prerequisites

If this is your first time releasing ubuntu-advantage-tools, you'll need to do the following before getting started:

* Add the team helper scripts to your PATH: [uss-tableflip](https://github.com/canonical/uss-tableflip).
* If you don't yet have a gpg key set up, follow the instructions
  [here](https://help.launchpad.net/YourAccount/ImportingYourPGPKey) to create a key,
  publish it to `hkp://keyserver.ubuntu.com`, and import it into Launchpad.
* Before you run `sbuild-it` for the first time, you'll need to set up a chroot for each Ubuntu release.
  Follow [these instructions](https://gist.github.com/smoser/14df5f0cd621e10d2282d7c90345e322#new-sbuild-creation)
  to create a chroot for each supported release.
* You must have launchpad already properly configured in your system in order to upload packages to the PPAs. Follow [this guide](https://help.launchpad.net/Packaging/PPA/Uploading) to get set up.

### I. Preliminary/staging release to team infrastructure
1. Create a release PR

    a. Move the desired commits from our `main` branch onto the desired release branch

      * This step is currently not well defined. We currently are using `release-27` for all `27.X` releases and have been cherry-picking/rebasing all commits from `main` into this branch for a release.

    b Create a new entry in the `debian/changelog` file:

      * You can do that by running ` dch --newversion <version-name>`
      * Remember to update the release from `UNRELEASED` to the ubuntu/devel release. Edit the version to look like: `27.2~21.10.1`, with the appropriate ua and ubuntu/devel version numbers.
      * Populate `debian/changelog` with the commits you have cherry-picked
      * You can do that by running `git log <first-cherry-pick-commit>..<last-cherry-pick-commit> | log2dch`
        * This will generate a list of commits that could be included in the changelog.
      * You don't need to include all of the commits generated. Remember that the changelog should
        be read by the user to understand the new features/modifications in the package. If you
        think a commit will not add that much to the user experience, you can drop it from the
        changelog
      * To structure the changelog you can use the other entries as example. But we basically try to
        keep this order: debian changes, new features/modifications, testing. Within each section, bullet points should be alphabetized.
        
    c. Create a PR on github into the release branch. Ask in the UA channel on mattermost for review.

2. After the release PR is merged, tag the head of the release branch with the version number, e.g. `27.1`. Push this tag to Github.

3. Build the package for all Ubuntu releases and upload to `ppa:ua-client/staging`

    a. Clone the repository in a clean directory and switch to the release branch
      * *WARNING* Build the package in a clean environment. The reason for that is because the package
        will contain everything that it is present in the folder. If you are storing credentials or
        other sensible development information in your folder, they will be uploaded too when we send
        the package to the ppa. A clean environment is the safest way to perform this.

    b. Edit the changelog:
      * List yourself as the author of this release.
      * Edit the version number to look like: `27.2~20.04.1-rc1` (`<version>~<ubuntu-release-number>.<revno>-rc<release-candidate-number>`)
      * Edit the ubuntu release name. Start with the ubuntu/devel release (e.g. `impish`).
      * `git commit -m "throwaway"` Do **not** push this commit!

    c. `build-package`
      * This script will generate all the package artifacts in the parent directory as `../out`.

    d. `sbuild-it ../out/<package_name>.dsc`
      * If this succeeds move on. If this fails, debug and fix before continuing.

    e. Repeat 3.b through 3.d for all supported Ubuntu Releases
      * PS: remember to also change the version number on the changelog. For example, suppose
        the new version is `1.1~20.04.1-rc1`. If you want to test Bionic now, change it to
        `1.1~18.04.1-rc1`.

    f. For each release, dput to the staging PPA:
      * `dput ppa:ua-client/staging ../out/<package_name>_source.changes`
      * After each `dput` wait for the "Accepted" email from Launchpad before moving on.

### II. Release to Ubuntu (devel and SRU)

> Note: `impish` is used throughout as a reference to the current devel release. This will change.

1. Prepare SRU Launchpad bugs.

    a. We do this even before a succesful merge into ubuntu/devel because the context added to these bugs is useful for the Server Team reviewer.

    b. Create a new bug on Launchpad for ubuntu-advantage-tools and use the format defined [here](https://wiki.ubuntu.com/UbuntuAdvantageToolsUpdates#SRU_Template) for the description.
      * The title should be in the format `[SRU] ubuntu-advantage-tools (27.1 -> 27.2) Xenial, Bionic, Focal, Hirsute`, substituting version numbers and release names as necessary.
    
    c. For each Launchpad bug fixed by this release (which should all be referenced in our changelog), add the SRU template to the description and fill out each section.
      * Leave the original description in the bug at the bottom under the header `[Original Description]`.
      * For the testing steps, include steps to reproduce the bug. Then include instructions for adding `ppa:ua-client/staging`, and steps to verify the bug is no longer present.

2. Set up the Merge Proposal (MP) for ubuntu/devel

    a. `git-ubuntu clone ubuntu-advantage-tools; cd ubuntu-advantage-tools`

    b. `git remote add upstream git@github.com:canonical/ubuntu-advantage-client.git`

    c. `git fetch upstream`

    d. `git rebase --onto pkg/ubuntu/devel <last-version-tag> <this-version-tag>`
      * e.g. `git rebase --onto pkg/ubuntu/devel 27.0.2 27.1`
      * You may need to resolve conflicts, but hopefully these will be minimal.
      * You'll end up in a detached state

    e. `git checkout -B upload-<this-version>-impish`
      * This creates a new local branch name based on your detached branch

    f. Make sure the changelog version contains the release version in the name (For example, `27.1~21.10.1`)

    g. `git push <your_launchpad_user> upload-<this-version>-impish`

    h. On Launchpad, create a merge proposal for this version which targets `ubuntu/devel`
      * For an example, see the [27.0.2 merge proposal](https://code.launchpad.net/~chad.smith/ubuntu/+source/ubuntu-advantage-tools/+git/ubuntu-advantage-tools/+merge/402459)
      * Add 2 review slots for `canonical-server` and `canonical-server-core-reviewers`
3. Set up the MP for past Ubuntu releases based on the ubuntu/devel PR

    a. Create a PR for each target series based off your local `release-${UA_VERSION}-impish` branch:
    ```bash
    UA_VERSION=<UA-VERSION>
    SRU_BUG=<SRU-BUG>
    LP_USER=<LAUNCHPAD-USERNAME>

    for release in xenial bionic focal groovy hirsute
    do
      rm ubuntu-advantage-*
      git checkout upload-${UA_VERSION}-impish -B upload-${UA_VERSION}-$release
      case "${release}" in
          xenial) version=${UA_VERSION}~16.04.1;;
          bionic) version=${UA_VERSION}~18.04.1;;
          focal) version=${UA_VERSION}~20.04.1;;
          groovy) version=${UA_VERSION}~20.10.1;;
          hirsute) version=${UA_VERSION}~21.04.1;;
      esac
      dch -v ${version} -D ${release} -b  "Backport new upstream release: (LP: #${SRU_BUG}) to $release"
      git commit -m "changelog backport to ${release}" debian/changelog
      git push $LP_USER upload-${UA_VERSION}-$release
    done
    ```

    b. Create merge proposals for each SRU target release @ `https://code.launchpad.net/~<YOUR_LP_USER></YOUR_LAUNCHPAD_USER>/ubuntu/+source/ubuntu-advantage-tools/+git/ubuntu-advantage-tools/`. Make sure each MP targets your `upload-${UA_VERSION}-impish` branch (the branch you are MP-ing into ubuntu/devel).

    c. Add both `canonical-server` and `canonical-server-core-reviewers` as review slots on each MP.

4. Server Team Review

    a. Ask in ~Server for a review of your MPs. Include a link to the primary MP into ubuntu/devel and mention the other MPs are only changelog MPs for the SRUs into past releases.
    
    b. If they request changes, create a PR into `main` on github and ask UAClient team for review. After a merge, open another PR on github, cherry-picking the change into the release branch. After that is merged, cherry-pick the commit into your `upload-<this-version>-impish` branch and push to launchpad. Then notify the Server Team member that you have addressed their requests. (This can probably be simplified).
      * Some issues may just be filed for addressing in the future if they are not urgent or pertinent to this release.
      * Unless the changes are very minor, or only testing related, you should upload a new release candidate version to `ppa:ua-client/staging` as descibed in I.3.

    c. Once review is complete and approved, confirm that Ubuntu Server approver will be tagging the PR with the appropriate `upload/<version>` tag so git-ubuntu will import rich commit history.

    d. Check `rmadison ubuntu-advantage-tools` for updated version in devel release

    e. Confirm availability in <devel>-updates pocket via `lxc launch ubuntu-daily:impish dev-i; lxc exec dev-i -- apt update; lxc exec dev-i -- apt-cache policy ubuntu-advantage-tools`
      * Note that any changes to the code after this point will likely require a bump in the patch version of the release.

    f. Ask Ubuntu Server approver if they also have upload rights to the proposed queue. If they do, request that they upload ubuntu-advantage-tools for all releases. If they do not, ask in ~Server channel for a Ubuntu Server team member with upload rights for an upload review of the MP for the proposed queue.

    g. Once upload review is complete and approved, confirm that Ubuntu Server approver will upload ua-tools via dput to the `-proposed` queue.

    h. Check the [-proposed release queue](https://launchpad.net/ubuntu/xenial/+queue?queue_state=1&queue_text=ubuntu-advantage-tools) for presence of ua-tools in unapproved state for each supported release. Note: libera chat #ubuntu-release IRC channel has a bot that reports queued uploads of any package in a message like "Unapproved: ubuntu-advantage-tools .. version".

5. SRU Review

    a. Once unapproved ua-tools package is listed in the pending queue for each target release, [ping appropriate daily SRU vanguard for review of ua-tools into -proposed](https://wiki.ubuntu.com/StableReleaseUpdates#Publishing)via the libera.chat #ubuntu-release channel

    b. As soon as the SRU vanguard approves the packages, a bot in #ubuntu-release will announce that ubuntu-advantage-tools is accepted into the applicable -proposed pockets, or the [Xenial -proposed release rejection queue](https://launchpad.net/ubuntu/xenial/+queue?queue_state=4&queue_text=ubuntu-advantage-tools) will contain a reason for rejections. Double check the SRU process bug for any actionable review feedback.

    c. Once accepted into `-proposed` by an SRU vanguard [ubuntu-advantage-tools shows up in the pending_sru page](https://people.canonical.com/~ubuntu-archive/pending-sru.html), check `rmadison ubuntu-advantage-tools | grep -proposed` to see if the upload exists in -proposed yet.

    d. Confirm availability in <devel>-proposed pocket via
    ```bash
    cat > setup_proposed.sh <<EOF
    #/bin/bash
    mirror=http://archive.ubuntu.com/ubuntu
    echo deb \$mirror \$(lsb_release -sc)-proposed main | tee /etc/apt/sources.list.d/proposed.list
    apt-get update -q;
    apt-get install -qy ubuntu-advantage-tools;
    apt-cache policy ubuntu-advantage-tools;
    EOF

    lxc launch ubuntu-daily:impish dev-i;
    lxc file push setup_proposed.sh
    lxc exec dev-i -- bash /setup_proposed.sh
    ```

    e. Once [ubuntu-advantage-tools shows up in the pending_sru page](https://people.canonical.com/~ubuntu-archive/pending-sru.html), perform the [Ubuntu-advantage-client SRU verification steps](https://wiki.ubuntu.com/UbuntuAdvantageToolsUpdates). This typically involves running all behave targets with `UACLIENT_BEHAVE_ENABLE_PROPOSED=1 UACLIENT_BEHAVE_CHECK_VERSION=<this-version>` and saving the output.

    f. After all tests have passed, tarball all of the output files and upload them to the SRU bug with a message that looks like this:
    ```
    We have run the full ubuntu-advantage-tools integration test suite against the version in -proposed. The results are attached. All tests passed (or call out specific explained failures).
    
    You can verify the correct version was used by checking the output of the first test in each file, which prints the version number.

    I am marking the verification done for this SRU.
    ```
    Change the tags on the bug from `verification-needed` to `verification-done` (including the verification tags for each release).

    g. For any other related Launchpad bugs that are fixed in this release. Perform the verification steps necessary for those bugs and mark them `verification-done` as needed. This will likely involve following the test steps, but instead of adding the staging PPA, enabling -proposed.

    h. Once all SRU bugs are tagged as `verification*-done`, all SRU-bugs should be listed as green in [the pending_sru page](https://people.canonical.com/~ubuntu-archive/pending-sru.html).
    
    i. After the pending_sru page says that ubuntu-advantage-tools has been in proposed for 7 days, it is now time to ping the [current SRU vanguard](https://wiki.ubuntu.com/StableReleaseUpdates#Publishing) for acceptance of ubuntu-advantage-tools into -updates.

### III. Final release to team infrastructure

1. Ensure the version tag is correct on github. The `version` git tag should point to the commit that was released as that version to ubuntu -updates. If changes were made in response to feedback during the release process, the tag may have to be moved.
2. Perform the steps from `I.3` above but don't include a `-rcX` in the version name, and upload to `ppa:ua-client/stable` instead of staging.
3. Bring in any changes that were made to the release branch into `main` via PR (e.g. Changelog edits).

## Ubuntu PRO Release Process

Below is the procedure used to release ubuntu-advantage-tools to Ubuntu PRO images:

 1. [Open Daily PPA copy-package operation](https://code.launchpad.net/~ua-client/+archive/ubuntu/daily/+copy-packages)
 2. Check Xenial, Bionic, Focal, Hirsute, Impish packages
 3. Select Destination PPA: UA Client Premium [~ua-client/ubuntu/staging]
 4. Select Destination series: The same series
 5. Copy options: "Copy existing binaries"
 6. Click Copy packages
 7. Notify Pro Image creators about expected Premium PPA version (patviafore/powersj)
