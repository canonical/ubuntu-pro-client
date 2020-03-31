# Ubuntu Advantage Client Releases

## Release versioning schemes:

Below are the versioning schemes used for publishing debs:

| Build target | Version Format |
| -------- | -------- |
| Devel series upstream release | XX.YY-<commit-revno>-g<commitish>~ubuntu1|
| Devel series bugfix release | XX.YY.Z-<commit-revno>-g<commitish>~ubuntu1|
| Stable series release | XX.YY-<commit-revno>-g<commitish>~ubuntu1~18.04.1|
| [Daily Build Recipe](https://code.launchpad.net/~canonical-server/+recipe/ua-client-daily) | XX.YY-<revtime>-g<commitish>-~ubuntu1~18.04.1 |

## Devel Release Process

Below is the procedure used to release ubuntu-advantage-client:

 1. create a release tarfile/changes file using uss-tableflip's build-package script
```
 ./tools/make-release <SERIES> <PPA_URL_FOR_TEST_UPLOADS>
 # follow printed procedure for dput to test PPA, and tag the released commitish
```

 2. Create an "upload a new version bug" in https://bugs.launchpad.net/ubuntu/+source/ubuntu-advantage-tools/+bugs

 3. Describe the need, provide testing PPA and describe test instuctions
 4. Ping appropriate maintainer about upload and verification
 5. Validate tests, accept upload and ship it
