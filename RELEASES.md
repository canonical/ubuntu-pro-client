# Ubuntu Advantage Client Releases

## Release versioning schemes:

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

## Devel Release Process

Below is the procedure used to release ubuntu-advantage-client to an Ubuntu series. It makes the following assumptions:
* The current ubuntu devel release is impish
* We are releasing version 27.1
* The previous release was 27.0.2
* The commits for 27.0.2 and 27.1 on https://github.com/canonical/ubuntu-advantage-client are tagged with `27.0.2` and `27.1` respectively.
  * These tags should be on the correct commits on the `release-27` branch
  * `27.1`, which is the tag of the release we are making, has not yet been uploaded to `pkg/ubuntu/devel`

 1. git-ubuntu clone ubuntu-advantage-tools; cd ubuntu-advantage-tools
 2. git remote add upstream git@github.com:canonical/ubuntu-advantage-client.git
 3. git fetch upstream
 4. git rebase --onto pkg/ubuntu/devel 27.0.2 27.1
 5. git checkout -B upload-27.1-impish # to create a new local branch name based on your detached branch in step 4
 6. Make sure the changelog version contains the release version on the name (For example, 27.1~21.10.1)
 7. git push `<your_launchpad_user>` upload-27.1-impish
 8. Create a PPA for upload reviewers at `https://launchpad.net/~<YOUR_LP_USER>/+activate-ppa`
 9. Push to your test PPA so upload reviewers can easily install and test packages during review
 ```bash
    debuild -S
    dput  ppa:<YOUR_LAUNCHPAD_USER>/ua-client-uploads ./ubuntu-advantage-tools_*_source.changes
```
 10. Create a merge proposal for 27.1 which targets `ubuntu/devel`
     * For an example, see the [27.0.2 merge proposal](https://code.launchpad.net/~chad.smith/ubuntu/+source/ubuntu-advantage-tools/+git/ubuntu-advantage-tools/+merge/402459)
 11. Add 2 review slots for `canonical-server` and `canonical-server-core-reviewers`

## SRU Release Process
Below is the procedure used to SRU ubuntu-advantage-client to a stable Ubuntu series. It makes the following assumptions:
* The procedure for the Devel Release Process has just completed
* A local git branch representing the MP most recently released to the Ubuntu devel release is `upload-27.1-impish`

 1. Create an "upload a new version bug" in https://bugs.launchpad.net/ubuntu/+source/ubuntu-advantage-tools/+bugs
   * Describe the need, provide testing PPA and describe test instructions
   * For examples, see [27.0](https://bugs.launchpad.net/ubuntu/+source/ubuntu-advantage-tools/+bug/1926361) or [20.3](https://bugs.launchpad.net/ubuntu/+source/ubuntu-advantage-tools/+bug/1869980)
 2. Create a PR for each target series based off your local `release-${UA_VERSION}-impish` branch:
 ```bash
 UA_VERSION=<UA-VERSION>
 SRU_BUG=<SRU-BUG>
 LP_USER=<LAUNCHPAD-USERNAME>

 for release in xenial bionic focal groovy hirsute
 do
  rm -rf ../out
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
  build-package # to create release-specific dsc files used to upload in step 16
  sbuild-it ../out/ubuntu-*.dsc
  git push $LP_USER upload-${UA_VERSION}-$release
 done
 ```
 3. Create merge proposals for each SRU target release @ `https://code.launchpad.net/~<YOUR_LP_USER></YOUR_LAUNCHPAD_USER>/ubuntu/+source/ubuntu-advantage-tools/+git/ubuntu-advantage-tools/`. Make sure each PR targets your `upload-${UA_VERSION}-impish` branch.
 4. Add both `canonical-server` and `canonical-server-core-reviewers` as review slots on the MP.
 5. Upload each release (including impish) to `ppa:ua-client/staging`
 ```bash
 for changes_file in ../out/*changes; do
   dput ppa:ua-client/staging $changes_file
 done
 ```
 6. Ping ~Server channel member with upload rights for a review of your MR
 7. Address MR review comments or file issues for future until MR accepted and uploaded to the [proper upload release queue](https://launchpad.net/ubuntu/hirsute/+queue?queue_state=1&queue_text=ubuntu-advantage-tools)
 8. Ping [appropriate daily SRU vanguard for acceptance of ua-tools into -proposed](https://wiki.ubuntu.com/StableReleaseUpdates#Publishing)FreeNode #ubuntu-release
 9. Once [ubuntu-advantage-tools shows up in the pending_sru page](https://people.canonical.com/~ubuntu-archive/pending-sru.html), perform the [Ubuntu-advantage-client SRU verification steps](https://wiki.ubuntu.com/UbuntuAdvantageToolsUpdates)
10. When SRU verification is complete, mark any SRU-related bugs with 'verification-done' tags as each bug, task, or release verified and completes successfully
11. Once all SRU bugs are tagged as `verification*-done`, all SRU-bugs should be listed as green in [the pending_sru page](https://people.canonical.com/~ubuntu-archive/pending-sru.html). It is now time to ping the [current SRU vanguard](https://wiki.ubuntu.com/StableReleaseUpdates#Publishing) for acceptance of ubuntu-advantage-tools into -updates

## Ubuntu PRO Release Process

Below is the procedure used to release ubuntu-advantage-tools to Ubuntu PRO images:

 1. [Open Daily PPA copy-package operation](https://code.launchpad.net/~ua-client/+archive/ubuntu/daily/+copy-packages)
 2. Check Trusty, Xenial, Bionic package
 3. Select Destination PPA: UA Client Premium [~ua-client/ubuntu/staging]
 4. Select Destination series: The same series
 5. Copy options: "Copy existing binaries"
 6. Click Copy packages
 7. Notify Pro Image creators about expected Premium PPA version (patviafore/rcj/powersj)


## Release to PPA

We manually upload the packages to our staging/stable PPAs. If you want to cut a new release and
upload to one of these PPAs, follow these steps:

 1. Do a `git cherry-pick` on the commits that should be included in the release
 2. Update the debian/changelog file:
    * Create a new entry in the `debian/changelog` file:
      * You can do that by running ` dch --newversion <version-name>`
      * Remember to update the release from `UNRELEASED` to the most recently supported
        ubuntu release
    * Populate `debian/changelog` with the commits you have cherry-picked
      * You can do that by running `git log <first-cherry-pick-commit>..<last-cherry-pick-commit> | log2dch`
      * This will generate a list of commits that could be included in the changelog. If you don't
        have `log2dch`, you can get it from the [uss-tableflip](https://github.com/canonical/uss-tableflip)
      * You don't need to include all of the commits generated. Remember that the changelog should
        be read by the user to understand the new features/modifications in the package. If you
        think a commit will not add that much to the user experience, you can drop it from the
        changelog
      * To structure the changelog you can use the other entries as example. But we basically try
        keep this order: debian changes, new features/modifications, testing
 3. Start building the package:
    * *WARNING* Build the package in a clean environment. The reason for that is because the package
      will contain everything that it is present in the folder. If you are storing credentials or
      other sensible development information in your folder, they will be uploaded too when we send
      the package to the ppa. A clean environment is the safest way to perform this.
    * Build the necessary artifacts that allow building the package
      * Guarantee that you have a gpg key in the system. You will use that gpg key to sign the
        package.
        * If you don't yet have a gpg key set up, follow the instructions
          [here](https://help.launchpad.net/YourAccount/ImportingYourPGPKey) to create a key,
          publish it to `hkp://keyserver.ubuntu.com`, and import it into Launchpad.
      * We can achieve that by running the `build-package` command when your current folder is the
        top of source tree. This script is also found on the [uss-tableflip](https://github.com/canonical/uss-tableflip) repo.
      * This script will generate all the package artifacts in the parent directory as `../out`.
    * Verify if we can build the package:
      * We can achieve that by running the `sbuild-it` command. This script is also found on the
        [uss-tableflip](https://github.com/canonical/uss-tableflip) repo.
      * Before you run `sbuild-it` for the first time, you'll need to set up a chroot for each Ubuntu release.
        Follow [these instructions](https://gist.github.com/smoser/14df5f0cd621e10d2282d7c90345e322#new-sbuild-creation)
        to create a chroot for each supported release.
      * To use it, you can just run `sbuild-it ../out/<package_name>.dsc
      * If the package was built sucessfully, you can move to the next step.
 4. Repeat that for older ubuntu releases:
    * Currently, we test this build process for `Trusty(14.04)`, `Xenial(16.04)`, `Bionic(18.04)`,
      `Focal(20.10)`, `Groovy(20.10)` and `Hirsute(21.04)`
    * To test this other releases, just change the changelog to target those releases.
      PS: remember to also change the version number on the changelog. For example, suppose
      the new version is `1.1~20.04.1`. If you want to test Bionic now, change it to
      `1.1~18.04.1`.
    * Commit those changes and perform the `build-package` and `sbuild-it` steps for the release.
      * These commits are just local commits for this build process - do not push them to remote repository.
 5. After all of the releases are tested, we can start uploading to the ppa. For each release, run
    the command `dput ppa:ua-client/stable ../out/<package_name>_source.changes`
    * Run this command for each release you are going to upload
    * Remember to have launchpad already properly configured in your system to allow you uploading
      packages to the ppa.
