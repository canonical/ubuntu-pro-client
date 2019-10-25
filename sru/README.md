# SRU: Collection of Stable Release Update integration tests
## Intent
This is a collection for scripts which have been manually run during the verification of ubuntu-advantage-client SRUs (Stable Release Updates). These scripts and their results were attached to each SRU process bug in order to pass SRU verification and publish that version of ubuntu-advantage-tools. Each subdirectory name will be the launchpad SRU process bug associated with that release. Within the subdir will be scripts that can be manually run to validate certain features of ubuntu-advantage-tools.

The hope is that we can codify these manual scripts into automated behave integration tests in the future and have less and less of this manual work in subsequent SRUs. In the meantime, have a pool of scripts that exercise certain aspects of ua-tools setup and teardown is helpful reference fo future SRUs, and behave integration test writing.

## SRU scripts


| SRU bug (series)| package version | Release date | Scripts |
| -------- | -------- | -------- | ------- |
| [Bug #1832757](https://bugs.launchpad.net/ubuntu/+source/ubuntu-advantage-tools/+bug/1832757) (trusty)    |  19.6~ubuntu14.04.2  | 11/05/2019 |  [esm-trusty-test-1.md](./1832757/esm-trusty-test-1.md)<br/>[esm-trusty-test-2.md](./1832757/esm-trusty-test-2.md)<br/>[esm-trusty-test-3.md](./1832757/esm-trusty-test-3.md)<br/>[esm-trusty-test-4.md](./1832757/esm-trusty-test-4.md)<br/>[esm-trusty-test-5.md](./1832757/esm-trusty-test-5.md)<br/> |
