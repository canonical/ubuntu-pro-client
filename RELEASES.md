# Ubuntu Advantage Client Releases

## Release versioning schemes:

Below are the versioning schemes used for publishing debs:

| Build target | Version Format |
| -------- | -------- |
| Devel series upstream release | XX.YY |
| Devel series bugfix release | XX.YY.Z~ubuntu1|
| Stable series release | XX.YY~ubuntu1~18.04.1|
| [Daily Build Recipe](https://code.launchpad.net/~canonical-server/+recipe/ua-client-daily) | XX.YY+<revtime>-g<commitish>~ubuntu1~18.04.1 |
| Ubuntu PRO series release | binary copies of Daily PPA |

## Supported upgrade use-cases based on version formats

| Upgrade path | Version diffs |
| LTS to LTS | 20.3~ubuntu1~14.04.1 -> 20.3~ubuntu1~16.04.1 |
| LTS to Daily PPA | 20.3~ubuntu1~14.04.1 -> 20.3+202004011202~ubuntu1~14.04.1 |
| Ubuntu PRO to latest <series>-updates | 20.3+202004011202~ubuntu1~14.04.1 -> 20.4~ubuntu1~14.04.1 |
| Ubuntu PRO to Daily PPA | 20.3+202004011202~ubuntu1~14.04.1 -> 20.4+202004021202~ubuntu1~14.04.1 |


## Devel Release Process

Below is the procedure used to release ubuntu-advantage-client to an Ubuntu series:

 1. git-ubuntu clone ubuntu-advantage-tools; cd ubuntu-advantage-tools
 2. git remote add upstream git@github.com:canonical/ubuntu-advantage-client.git
 3. git fetch upstream
 4. git checkout upstream/release-24
 5. git tag -a 24.3
 6. git rebase --onto pkg/ubuntu/devel 24.2 24.3
 7. git checkout -b pkg-upload-24.3
 8. debuild -S
 9. dput  ppa:chad.smith/ua-client-uploads ./ubuntu-advantage-tools_24.3_source.changes
 10. create a release tarfile/changes file using uss-tableflip's build-package script
```
 ./tools/make-release --series <SERIES> --ppa <PPA_URL_FOR_TEST_UPLOADS>
 # follow printed procedure for dput to test PPA, and tag the released commitish
```
 11. Create a merge proposal such as [24.2 PR](https://code.launchpad.net/~chad.smith/ubuntu/+source/ubuntu-advantage-tools/+git/ubuntu-advantage-tools/+merge/385073), [24.3 PR](https://code.launchpad.net/~chad.smith/ubuntu/+source/ubuntu-advantage-tools/+git/ubuntu-advantage-tools/+merge/389745)
 11. For SRUs: Create an "upload a new version bug" in https://bugs.launchpad.net/ubuntu/+source/ubuntu-advantage-tools/+bugs
 12. Describe the need, provide testing PPA and describe test instructions
 13. Ping appropriate maintainer about upload and verification
 14. Validate tests, accept upload and ship it

Previous release bugs:
| ------- |
| [20.3 Focal](https://bugs.launchpad.net/ubuntu/+source/ubuntu-advantage-tools/+bug/1869980) |


## Ubuntu PRO Release Process

Manually perform a binary package copy from Daily PPA to Premium PPA and notify image creators

 1. [Open Daily PPA copy-package operation](https://code.launchpad.net/~ua-client/+archive/ubuntu/daily/+copy-packages)
 2. Check Trusty, Xenial, Bionic package
 3. Select Destination PPA: UA Client Premium [~ua-client/ubuntu/staging]
 4. Select Destination series: The same series
 5. Copy options: "Copy existing binaries"
 6. Click Copy packages
 7. Notify Pro Image creators about expected Premium PPA version (patviafore/rcj/powersj)
