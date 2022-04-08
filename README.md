<h1>
  <a href="https://ubuntu.com/advantage" target="_blank">
    <img src="./.assets/circle_of_friends.png" width="33"/>
  </a>
  <br>
  Ubuntu Advantage Client
</h1>

###### Clean and Consistent CLI for your Ubuntu Advantage Systems

![Latest Version](https://img.shields.io/github/v/tag/canonical/ubuntu-advantage-client.svg?label=Latest%20Version)
![CI](https://github.com/canonical/ubuntu-advantage-client/actions/workflows/ci-base.yaml/badge.svg?branch=main)

The Ubuntu Advantage (UA) Client provides users with a simple mechanism to
view, enable, and disable offerings from Canonical on their system. The
following entitlements are supported:

- [Common Criteria EAL2 certification artifacts provisioning](https://ubuntu.com/cc-eal)
- [Canonical CIS Benchmark Audit Tool](https://ubuntu.com/cis-audit)
- [Ubuntu Extended Security Maintenance](https://ubuntu.com/esm)
- [Robot Operating System Extended Security Maintenance](https://ubuntu.com/robotics/ros-esm)
- [FIPS 140-2 Certified Modules](https://ubuntu.com/fips)
- [FIPS 140-2 Non-Certified Module Updates](https://ubuntu.com/fips)
- [Livepatch Service](https://www.ubuntu.com/livepatch)

## Obtaining the Client

The client comes pre-installed on all Ubuntu systems in the debian
`ubuntu-advantage-tools` package. "Ubuntu Pro" images on AWS, Azure and GCP
will also contain `ubuntu-advantage-pro` which automates machine attach
on boot for custom AWS, Azure and GCP images.

Ubuntu Pro images are available on the following cloud platforms on all Ubuntu LTS releases (Xenial, Bionic, Focal):
1. AWS: [Ubuntu PRO](https://ubuntu.com/aws/pro) and [Ubuntu PRO FIPS](https://ubuntu.com/aws/fips)
2. Azure: [Ubuntu PRO](https://ubuntu.com/azure/pro) and [Ubuntu PRO FIPS](https://ubuntu.com/azure/fips)
3. GCP: [Ubuntu PRO](https://ubuntu.com/gcp/pro)

Additionally, there are 3 PPAs with different release channels of the Ubuntu Advantage Client:

1. Stable: This contains stable builds only which have been verified for release into Ubuntu stable releases or Ubuntu PRO images.
    - add with `sudo add-apt-repository ppa:ua-client/stable`
2. Staging: This contains builds under validation for release to stable Ubuntu releases and images
    - add with `sudo add-apt-repository ppa:ua-client/staging`
3. Daily: This PPA is updated every day with the latest changes.
    - add with `sudo add-apt-repository ppa:ua-client/daily`

Users can manually run the `ua` command to learn more or view the manpage.

## User Documentation

### Tutorials

* [Create a FIPS compliant Ubuntu Docker image](./docs/tutorials/create_a_fips_docker_image.md)

### How To Guides

* [How to Configure Proxies](./docs/howtoguides/configure_proxies.md)
* [How to Enable Ubuntu Advantage Services in a Dockerfile](./docs/howtoguides/enable_ua_in_dockerfile.md)
* [How to Create a custom Golden Image based on Ubuntu Pro](./docs/howtoguides/create_pro_golden_image.md)

### Reference

* [Ubuntu Release and Architecture Support Matrix](./docs/reference/support_matrix.md)

## Terminology
 The following vocabulary is used to describe different aspects of the work
Ubuntu Advantage Client performs:

| Term | Meaning |
| -------- | -------- |
| UA Client | The python command line client represented in this ubuntu-advantage-client repository. It is installed on each Ubuntu machine and is the entry-point to enable any Ubuntu Advantage commercial service on an Ubuntu machine. |
| Contract Server | The backend service exposing a REST API to which UA Client authenticates in order to obtain contract and commercial service information and manage which support services are active on a machine.|
| Entitlement/Service | An Ubuntu Advantage commercial support service such as FIPS, ESM, Livepatch, CIS-Audit to which a contract may be entitled |
| Affordance | Service-specific list of applicable architectures and Ubuntu series on which a service can run |
| Directives | Service-specific configuration values which are applied to a service when enabling that service |
| Obligations | Service-specific policies that must be instrumented for support of a service. Example: `enableByDefault: true` means that any attached machine **MUST** enable a service on attach |

### Pro Upgrade Daemon
UA client sets up a daemon on supported platforms (currently GCP only) to
detect if an Ubuntu Pro license is purchased for the machine. If a Pro license
is detected, then the machine is automatically attached.

If you are uninterested in UA services, you can safely stop and disable the
daemon using systemctl:

```
sudo systemctl stop ubuntu-advantage.service
sudo systemctl disable ubuntu-advantage.service
```

## Contributing to ubuntu-advantage-tools
See [CONTRIBUTING.md](CONTRIBUTING.md)
