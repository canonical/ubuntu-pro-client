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

 1. create a release tarfile/changes file using uss-tableflip's build-package script
```
 ./tools/make-release --series <SERIES> --ppa <PPA_URL_FOR_TEST_UPLOADS>
 # follow printed procedure for dput to test PPA, and tag the released commitish
```

 2. Create an "upload a new version bug" in https://bugs.launchpad.net/ubuntu/+source/ubuntu-advantage-tools/+bugs

 3. Describe the need, provide testing PPA and describe test instuctions
 4. Ping appropriate maintainer about upload and verification
 5. Validate tests, accept upload and ship it


## Ubuntu PRO Release Process

Manually perform a binary package copy from Daily PPA to Premium PPA and notify image creators

 1. [Open Daily PPA copy-package operation](https://code.launchpad.net/~canonical-server/+archive/ubuntu/ua-client-daily/+copy-packages)
 2. Check Trusty, Xenial, Bionic package
 3. Select Destination PPA: UA Client Premium [~canonical-server/ubuntu/ua-client-premium]
 4. Select Destination series: The same series
 5. Copy options: "Copy existing binaries
 6. Click Copy packages
 7. Notify Pro Image creatros about expected Premium PPA version (patviafore/rcj)
