<h1>
  <a href="https://ubuntu.com/advantage" target="_blank">
    <img src="./.assets/circle_of_friends.png" width="33"/>
  </a>
  <br>
  Ubuntu Advantage Client
</h1>

###### Clean and Consistent CLI for your Ubuntu Advantage Systems
![Latest Upstream Version](https://img.shields.io/github/v/tag/canonical/ubuntu-advantage-client.svg?label=Latest%20Upstream%20Version&logo=github&logoColor=white&color=33ce57)
![CI](https://github.com/canonical/ubuntu-advantage-client/actions/workflows/ci-base.yaml/badge.svg?branch=main)
<br/>
![Released Xenial Version](https://img.shields.io/ubuntu/v/ubuntu-advantage-tools/xenial?label=Xenial&logo=ubuntu&logoColor=white)
![Released Bionic Version](https://img.shields.io/ubuntu/v/ubuntu-advantage-tools/bionic?label=Bionic&logo=ubuntu&logoColor=white)
![Released Focal Version](https://img.shields.io/ubuntu/v/ubuntu-advantage-tools/focal?label=Focal&logo=ubuntu&logoColor=white)
![Released Jammy Version](https://img.shields.io/ubuntu/v/ubuntu-advantage-tools/jammy?label=Jammy&logo=ubuntu&logoColor=white)

The Ubuntu Advantage (UA) Client provides users with a simple mechanism to
view, enable, and disable offerings from Canonical on their system. The
following entitlements are supported:

- [Common Criteria EAL2 Certification Tooling](https://ubuntu.com/security/cc)
- [CIS Benchmark Audit Tooling](https://ubuntu.com/security/cis)
- [Ubuntu Security Guide (USG) Tooling](https://ubuntu.com/security/certifications/docs/usg)
- [Ubuntu Extended Security Maintenance (ESM)](https://ubuntu.com/security/esm)
- [Robot Operating System (ROS) Extended Security Maintenance](https://ubuntu.com/robotics/ros-esm)
- [FIPS 140-2 Certified Modules](https://ubuntu.com/security/fips)
- [FIPS 140-2 Non-Certified Module Updates](https://ubuntu.com/security/fips)
- [Livepatch Service](https://ubuntu.com/security/livepatch)

## Obtaining the Client

The client comes pre-installed on all Ubuntu systems in the debian `ubuntu-advantage-tools` package.

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

* [Getting started with UA](./docs/tutorials/basic_ua_commands.md)
* [Create a FIPS compliant Ubuntu Docker image](./docs/tutorials/create_a_fips_docker_image.md)

### How To Guides

* [How to get an UA token and attach to a subscription?](./docs/howtoguides/get_token_and_attach.md)
* [How to Configure Proxies](./docs/howtoguides/configure_proxies.md)
* [How to Enable Ubuntu Advantage Services in a Dockerfile](./docs/howtoguides/enable_ua_in_dockerfile.md)
* [How to Create a custom Golden Image based on Ubuntu Pro](./docs/howtoguides/create_pro_golden_image.md)
* [How to Manually update MOTD and APT messages](./docs/howtoguides/update_motd_messages.md)
* [How to enable CIS](./docs/howtoguides/enable_cis.md)
* [How to enable CC EAL](./docs/howtoguides/enable_cc.md)
* [How to enable ESM Infra](./docs/howtoguides/enable_esm_infra.md)
* [How to enable FIPS](./docs/howtoguides/enable_fips.md)
* [How to enable Livepatch](./docs/howtoguides/enable_livepatch.md)
* [How to configure a timer job?](./docs/howtoguides/configuring_timer_jobs.md)
* [How to attach with a configuration file?](./docs/howtoguides/how_to_attach_with_config_file.md)
* [How to collect UA logs?](./docs/howtoguides/how_to_collect_ua_logs.md)

### Reference

* [Ubuntu Release and Architecture Support Matrix](./docs/references/support_matrix.md)
* [UA Network Requirements](./docs/references/network_requirements.md)

### Explanation

* [What is the daemon for? (And how to disable it)](./docs/explanations/what_is_the_daemon.md)
* [What is Ubuntu PRO?](./docs/explanations/what_is_ubuntu_pro.md)
* [What is the ubuntu-advantage-pro package?](./docs/explanations/what_is_the_ubuntu_advantage_pro_package.md)
* [What are the timer jobs?](./docs/explanations/what_are_the_timer_jobs.md)

## Contributing
See [CONTRIBUTING.md](CONTRIBUTING.md)
