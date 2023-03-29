# Version string formatting

Below are the versioning schemes used for publishing debs:

| Build target                                                                      | Version Format                             |
| --------------------------------------------------------------------------------- | ------------------------------------------ |
| [Daily PPA](https://code.launchpad.net/~canonical-server/+recipe/ua-client-daily) | `XX.YY-<revno>~g<commitish>~ubuntu22.04.1` |
| Staging PPA                                                                       | `XX.YY~22.04~rc1`                        |
| Stable PPA                                                                        | `XX.YY~22.04~stableppa1`                 |
| Archive release                                                                   | `XX.YY~22.04`                            |
| Archive bugfix release                                                            | `XX.YY.Z~22.04`                          |

## Supported upgrade paths on same upstream version

Regardless of source, the latest available "upstream version" (e.g. 27.4) will always be installed, because the upstream version comes first followed by a tilde in all version formats.

This table demonstrates upgrade paths between sources for one particular upstream version.

| Upgrade path                    | Version diff example                                                    |
| ------------------------------- | ----------------------------------------------------------------------- |
| Staging to Next Staging rev     | `31.4~22.04~rc1` ➜ `31.4~22.04~rc2`                                 |
| Staging to Stable               | `31.4~22.04~rc2` ➜ `31.4~22.04~stableppa1`                          |
| Stable to Next Stable rev       | `31.4~22.04~stableppa1` ➜ `31.4~22.04~stableppa2`                   |
| Stable to Archive               | `31.4~22.04~stableppa2` ➜ `31.4~22.04`                              |
| LTS Archive to Next LTS Archive | `31.4~22.04` ➜ `31.4~24.04`                                         |
| Archive to Daily                | `31.4~24.04` ➜ `31.4-1500~g75fa134~ubuntu24.04.1`                     |
| Daily to Next Daily             | `31.4-1500~g75fa134~ubuntu24.04.1` ➜ `31.4-1501~g3836375~ubuntu24.04.1` |
