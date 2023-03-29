# Ubuntu Pro Client releases

## Background

The release process for ubuntu-advantage-tools has three overarching steps/goals.

1. Release to our team infrastructure. This includes GitHub and the `ua-client` PPAs.
2. Release to the latest Ubuntu devel release.
3. Release to the supported Ubuntu past releases via [SRU](https://wiki.ubuntu.com/StableReleaseUpdates) using the [ubuntu-advantage-tools specific SRU process](https://wiki.ubuntu.com/UbuntuAdvantageToolsUpdates).

Generally speaking, these steps happen in order, but there is some overlap. Also we may backtrack if issues are found part way through the process.

An average release should take somewhere between 10 and 14 calendar days if things go smoothly, starting at the decision to release and ending at the new version being available in all supported Ubuntu releases. Note that it is not 2 weeks of full time work. Most of the time is spent waiting for review or sitting in proposed.

> **Warning**
> If the release contains any change listed in the [Early Review Sign-Off list](../references/early_review_signoff.md), make sure it was properly reviewed *before* starting the release process. Ideally they would be reviewed even before implementation, but if some feature is in the list and didn't get a proper review, now is the time to do so.

## Prerequisites

If this is your first time releasing ubuntu-advantage-tools, you'll need to do the following before getting started:

* Add the team helper scripts to your PATH: [uss-tableflip](https://github.com/canonical/uss-tableflip).
* If you don't yet have a gpg key set up, follow the instructions
  [here](https://help.launchpad.net/YourAccount/ImportingYourPGPKey) to create a key,
  publish it to `hkp://keyserver.ubuntu.com`, and import it into Launchpad.
* Before you run `sbuild-it` for the first time, you'll need to set up a chroot for each Ubuntu release.
  Run the following to set up chroots with dependencies pre-installed for each release:
  ```bash
  apt-get install sbuild-launchpad-chroot
  bash ./tools/setup_sbuild.sh # This will give you usage information on how to call it with the correct parameters
  ```
* You must have Launchpad already properly configured in your system in order to upload packages to the PPAs. Follow [this guide](https://help.launchpad.net/Packaging/PPA/Uploading) to get set up.

* In order to run the `ppa` command, install `ppa-dev-tools` from `bryce`'s PPA:
  ```bash
  sudo add-apt-repository ppa:bryce/ppa-dev-tools
  sudo apt update
  sudo apt install ppa-dev-tools
  ```
  When running `ppa` for the first time, there will be another round of launchpad authorization to be performed.

## I. Preliminary/staging release to team infrastructure
1. Create a release PR:

    a. Move the desired commits from our `main` branch onto the desired release branch.

      * This step is currently not well defined. We currently are using `release-27` for all `27.X` releases and have been cherry-picking/rebasing all commits from `main` into this branch for a release.

    b Create a new entry in the `debian/changelog` file:

      * You can do that by running `dch --newversion <version-name>`.
      * Remember to update the release from `UNRELEASED` to the ubuntu/devel release. Edit the version to look like: `27.2~21.10`, with the appropriate pro-client and ubuntu/devel version numbers.
      * Populate `debian/changelog` with the commits you have cherry-picked.
      * You can do that by running `git log <first-cherry-pick-commit>..<last-cherry-pick-commit> | log2dch`
        * This will generate a list of commits that could be included in the changelog.
      * You don't need to include all of the commits generated. Remember that the changelog should
        be read by the user to understand the new features/modifications in the package. If you
        think a commit will not add that much to the user experience, you can drop it from the
        changelog.
      * To structure the changelog you can use the other entries as example. But we basically try to
        keep this order: debian changes, new features/modifications, testing. Within each section, bullet points should be alphabetized.
        
    c. Create a PR on GitHub into the release branch. Ask in the ~UA channel on Mattermost for review.

    d. When reviewing the release PR, please use the following guidelines when reviewing the new changelog entry:

       * Is the version correctly updated? We must ensure that the new version in the changelog is
         correct and it also targets the latest Ubuntu release at the moment.
       * Is the entry useful for the user? The changelog entries should be user focused, meaning
         that we should only add entries that we think users will care about (i.e. we don't need
         entries when fixing a test, as this doesn't provide meaningful information to the user).
       * Is this entry redundant? Sometimes we may have changes that affect separate modules of the
         code. We should have an entry only for the module that was most affected by it.
       * Is the changelog entry unique? We need to verify that the changelog entry is not already
         reflected in an earlier version of the changelog. If it is, we need not only to remove but double
         check the process we are using to cherry-pick the commits.
       * Is this entry actually reflected in the code? Sometimes, we can have changelog entries
         that are not reflected in the code anymore. This can happen during development when we are
         still unsure about the behaviour of a feature or when we fix a bug that removes the code
         that was added. We must verify each changelog entry that is added to be sure of their
         presence in the product.

2. After the release PR is merged, tag the head of the release branch with the version number, e.g., `27.1`. Push this tag to GitHub.

3. Build the package for all Ubuntu releases and upload to `ppa:ua-client/staging`:

    a. Clone the repository into a clean directory and switch to the release branch.
      * *WARNING* Build the package in a clean environment. The reason is that the package
        will contain everything that is present in the folder. If you are storing credentials or
        other sensible development information in your folder, they will be uploaded too when we send
        the package to the ppa. A clean environment is the safest way to perform this.

    b. Edit the changelog
      * List yourself as the author of this release.
      * Edit the version number to look like: `27.2~20.04~rc1` (`<version>~<ubuntu-release-number>~rc<release-candidate-number>`)
      * Edit the Ubuntu release name. Start with the ubuntu/devel release.
      * `git add debian/changelog && git commit -m "throwaway"` - Do **not** push this commit!

    c. `build-package`
      * This script will generate all the package artefacts in the parent directory as `../out`.

    d. `sbuild-it ../out/<package_name>.dsc`
      * If this succeeds move on. If this fails, debug and fix before continuing.

    e. Repeat 3.b through 3.d for all supported Ubuntu Releases
      * PS: remember to also change the version number on the changelog. For example, suppose
        the new version is `1.1~20.04~rc1`. If you want to test Bionic now, change it to
        `1.1~18.04~rc1`.

    f. For each release, dput to the staging PPA:
      * `dput ppa:ua-client/staging ../out/<package_name>_source.changes`
      * After each `dput` wait for the "Accepted" email from Launchpad before moving on.

## II. Release to Ubuntu (devel and SRU)

> **Note**
> `kinetic` is used throughout as a reference to the current devel release. This will change.

1. Prepare SRU Launchpad bugs.

    a. We do this even before a successful merge into ubuntu/devel because the context added to these bugs is useful for the Server Team reviewer.

    b. Create a new bug on Launchpad for ubuntu-advantage-tools and use the format defined [here](https://wiki.ubuntu.com/UbuntuAdvantageToolsUpdates#SRU_Template) for the description.
      * The title should be in the format `[SRU] ubuntu-advantage-tools (27.1 -> 27.2) Xenial, Bionic, Focal, Jammy`, substituting version numbers and release names as necessary.
      * If any of the changes for the SRU is in the [Early Review Sign-off list](../references/early_review_signoff.md), include a pointer in the `[Discussion]` section to where the discussion/approval of that feature took place (if possible).
    
    c. For each Launchpad bug fixed by this release (which should all be referenced in our changelog), add the SRU template to the description and fill out each section.
      * Leave the original description in the bug at the bottom under the header `[Original Description]`.
      * For the testing steps, include steps to reproduce the bug. Then include instructions for adding `ppa:ua-client/staging`, and steps to verify the bug is no longer present.

2. Set up the Merge Proposal (MP) for ubuntu/devel:

    a. `git-ubuntu clone ubuntu-advantage-tools; cd ubuntu-advantage-tools`

    b. `git remote add upstream git@github.com:canonical/ubuntu-advantage-client.git`

    c. `git fetch upstream`

    d. `git rebase --onto pkg/ubuntu/devel <last-version-tag> <this-version-tag>`
      * e.g. `git rebase --onto pkg/ubuntu/devel 27.0.2 27.1`
      * You may need to resolve conflicts, but hopefully these will be minimal.
      * You'll end up in a detached state.

    e. `git checkout -B upload-<this-version>-kinetic`
      * This creates a new local branch name based on your detached branch.

    f. Make sure the changelog version contains the release version in the name (e.g., `27.1~22.10`)

    g. `git push <your_launchpad_user> upload-<this-version>-kinetic`

    h. On Launchpad, create a merge proposal for this version which targets `ubuntu/devel`
      * For an example, see the [27.14.1 merge proposal](https://code.launchpad.net/~renanrodrigo/ubuntu/+source/ubuntu-advantage-tools/+git/ubuntu-advantage-tools/+merge/439507).
      * Add 2 review slots for `canonical-server-reporter` and `canonical-server-core-reviewers`.

    i. With the packages published to `ppa:ua-client/staging`, add links to the autopkgtest triggers to the Merge Proposal. The reviewer will have permission to trigger those tests. The links can be obtained by running `ppa tests -r <release> -a <arch1,arch2> ua-client/staging -L`
      * Make sure to post links to all the architectures built for a given release.
      * The riscv64 autopkgtests are not avaialble and don't need to be included.
      * The `ppa test` command will have two variations of tests: the regular one, and one with `all-proposed=1`; only the regular test need to be there.

4. Server Team Review and Pre-SRU Review

    a. Ask the assigned ubuntu-advantage-tools reviewer/sponsor from Server team for a review of your MPs. If you don't know who that is, ask in ~Server. Include a link to the ubuntu/devel MP and to the SRU bug.
    
    b. If they request changes, create a PR into the release branch on GitHub and ask Pro Client team for review. After that is merged, cherry-pick the commit into your `upload-<this-version>-<devel-release>` branch and push to launchpad. Then notify the Server Team member that you have addressed their requests.
      * Some issues may just be filed for addressing in the future if they are not urgent or pertinent to this release.
      * Unless the changes are very minor, or only testing related, you should upload a new release candidate version to `ppa:ua-client/staging` as described in I.3.
      * After the release is finished, any commits that were merged directly into the release branch in this way should be brought back into `main` via a single PR.

    c. Once review is complete and approved, the Server Team member should **not** upload the version to the devel release.
      * If they do, then any changes to the code after this point will require a bump in the patch version of the release.

    d. Now ask the SRU team for a pre-SRU review of the same MP. Mention that the exact same code will be released to all stable Ubuntu releases.
      * Follow instructions in `II.4.b` if they request any changes.

    e. Once the SRU team member gives a pre-SRU approval, create the branches for each stable release. They should be named `upload-<this-version>-<codename>`.
      * If you've followed the instructions precisely so far, you can just run `bash tools/create-lp-release-branches.sh`.

    f. Ask Server team member sponsor to upload to devel, and then the SRU proposed queue using the stable release branches you just created.
      * Ask them to tag the PR with the appropriate `upload/<version>` tag so git-ubuntu will import rich commit history.
      * If they do not have upload rights to the proposed queue, ask in ~Server channel for a Ubuntu Server team member with upload rights for an upload review of the MP for the proposed queue.

    g. Check the [-proposed release queue](https://launchpad.net/ubuntu/xenial/+queue?queue_state=1&queue_text=ubuntu-advantage-tools) for presence of ubuntu-advantage-tools in unapproved state for each supported release. Note: libera chat #ubuntu-release IRC channel has a bot that reports queued uploads of any package in a message like "Unapproved: ubuntu-advantage-tools .. version".

    h. Tell the SRU team member who performed the pre-SRU review that the packages are in the -proposed release queue. They will need to actually approve the package to move into -proposed.

5. -proposed verification and release to -updates

    a. As soon as the SRU vanguard approves the packages, a bot in #ubuntu-release will announce that ubuntu-advantage-tools is accepted into the applicable -proposed pockets, or the [Xenial -proposed release rejection queue](https://launchpad.net/ubuntu/xenial/+queue?queue_state=4&queue_text=ubuntu-advantage-tools) will contain a reason for rejections. Double check the SRU process bug for any actionable review feedback.
      * Once accepted into `-proposed` by an SRU vanguard [ubuntu-advantage-tools shows up in the pending_sru page](https://people.canonical.com/~ubuntu-archive/pending-sru.html), check `rmadison ubuntu-advantage-tools | grep -proposed` to see if the upload exists in -proposed yet.
      * Also actually check that the packages are accessible in a container by [enabling proposed](https://wiki.ubuntu.com/Testing/EnableProposed) and updating the package.

    b. With the package in proposed, perform the steps from `I.3` above but use a `~stableppaX` suffix instead of `~rcX` in the version name, and upload to `ppa:ua-client/stable` instead of staging.

    c. Perform the [Ubuntu-advantage-client SRU verification steps](https://wiki.ubuntu.com/UbuntuAdvantageToolsUpdates). This typically involves running all behave targets with `UACLIENT_BEHAVE_ENABLE_PROPOSED=1 UACLIENT_BEHAVE_CHECK_VERSION=<this-version>` and saving the output.
      * There may also be one-time test scripts added in the `sru/` directory for this release.

    d. After all tests have passed, tarball all of the output files and upload them to the SRU bug with a message that looks like this:
    ```
    We have run the full ubuntu-advantage-tools integration test suite against the version in -proposed. The results are attached. All tests passed.
    
    You can verify the correct version was used by checking the output of the first test in each file, which prints the version number.

    I am marking the verification done for this SRU.
    ```
    Change the tags on the bug from `verification-needed` to `verification-done` (including the verification tags for each Ubuntu release).

    e. For any other related Launchpad bugs that are fixed in this release, perform the verification steps necessary for those bugs and mark them `verification-done` as needed. This will likely involve following the test steps, but instead of adding the staging PPA, enabling -proposed.

    f. Once all SRU bugs are tagged as `verification*-done`, all SRU-bugs should be listed as green in [the pending_sru page](https://people.canonical.com/~ubuntu-archive/pending-sru.html).
    
    g. After the pending SRU page says that ubuntu-advantage-tools has been in proposed for 7 days, it is now time to ping the [current SRU vanguard](https://wiki.ubuntu.com/StableReleaseUpdates#Publishing) for acceptance of ubuntu-advantage-tools into -updates.

    h. Check `rmadison ubuntu-advantage-tools` for updated version in -updates.
      * Also actually check that the packages are accessible in a container and updating the package.

## III. Post-release updates

1. Ensure the version tag is correct on GitHub. The `version` git tag should point to the commit that was released as that version to ubuntu -updates. If changes were made in response to feedback during the release process, the tag may have to be moved.
2. Bring in any changes that were made to the release branch into `main` via PR (e.g., changelog edits).
3. Move any scripts added in `sru/` to a new folder in `sru/_archive` for the release.
4. Tell CPC that there is a new version of `ubuntu-advantage-tools` in -updates for all series.
