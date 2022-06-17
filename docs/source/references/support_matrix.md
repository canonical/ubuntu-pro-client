# Support Matrix for the client

Ubuntu Advantage services are only available on Ubuntu Long Term Support (LTS) releases.

On interim Ubuntu releases, `ua status` will report most of the services as 'n/a' and disallow enabling those services.

Below is a list of platforms and releases ubuntu-advantage-tools supports

| Ubuntu Release | Build Architectures                                | Support Level              |
| -------------- | -------------------------------------------------- | -------------------------- |
| Trusty         | amd64, arm64, armhf, i386, powerpc, ppc64el        | Last release 19.6          |
| Xenial         | amd64, arm64, armhf, i386, powerpc, ppc64el, s390x | Active SRU of all features |
| Bionic         | amd64, arm64, armhf, i386, ppc64el, s390x          | Active SRU of all features |
| Focal          | amd64, arm64, armhf, ppc64el, riscv64, s390x       | Active SRU of all features |
| Groovy         | amd64, arm64, armhf, ppc64el, riscv64, s390x       | Last release 27.1          |
| Hirsute        | amd64, arm64, armhf, ppc64el, riscv64, s390x       | Last release 27.5          |
| Impish         | amd64, arm64, armhf, ppc64el, riscv64, s390x       | Active SRU of all features |

Note: ppc64el will not have all APT messaging due to insufficient golang support
