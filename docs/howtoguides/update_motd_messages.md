# How to update MOTD and APT messages

Since ubuntu-advantage-tools is responsible for enabling ESM services, we advertise them on different
applications thorough the system, such as MOTD and apt commands like upgrade.

To verify that APT and MOTD message is advertising the ESM packages, ensure that we have ESM
source list files in the system. If that is the case, please run the following command to
update the state of MOTD and APT messages:

```sh
pro refresh messages
```
