# Building

Packages ubuntu-advantage-tools and ubuntu-advantage-pro are created from the
debian/control file in this repository. You can build the
packages the way you would normally build a Debian package:


```shell
dpkg-buildpackage -us -uc
```

> **Note**
> It will build the packages with dependencies for the Ubuntu release on
> which you are building, so it's best to build in a container or kvm for the
> release you are targeting.

OR, if you want to build for a target release other than the release
you're on:

## using sbuild
[configure sbuild](https://wiki.ubuntu.com/SimpleSbuild) and
use that for the build:

Setup some chroots for sbuild with this script
```shell
bash ./tools/setup_sbuild.sh
```

```shell
debuild -S
sbuild --dist=<target> ../ubuntu-advantage-tools_*.dsc
# emulating different architectures in sbuild-launchpad-chroot
sbuild-launchpad-chroot create --architecture="riscv64" "--name=focal-riscv64" "--series=focal"
```

> **Note**
> Every so often, it is recommended to update your chroots.
> ```bash
> # to update a single chroot
> sudo sbuild-launchpad-chroot update -n ua-xenial-amd64
> # this script can be used to update all chroots
> sudo PATTERN=\* sh /usr/share/doc/sbuild/examples/sbuild-debian-developer-setup-update-all
> ```
