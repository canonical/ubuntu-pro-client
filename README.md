<h1>
  <a href="https://ubuntu.com/pro" target="_blank">
    <img src="./docs/_static/circle_of_friends.png" width="33"/>
  </a>
  <br>
  Ubuntu Pro Client
</h1>

###### Clean and Consistent CLI for your Ubuntu Pro Systems
![Latest Upstream Version](https://img.shields.io/github/v/tag/canonical/ubuntu-advantage-client.svg?label=Latest%20Upstream%20Version&logo=github&logoColor=white&color=33ce57)
![CI](https://github.com/canonical/ubuntu-advantage-client/actions/workflows/ci-base.yaml/badge.svg?branch=main)
<br/>
![Released Xenial Version](https://img.shields.io/ubuntu/v/ubuntu-advantage-tools/xenial?label=Xenial&logo=ubuntu&logoColor=white)
![Released Bionic Version](https://img.shields.io/ubuntu/v/ubuntu-advantage-tools/bionic?label=Bionic&logo=ubuntu&logoColor=white)
![Released Focal Version](https://img.shields.io/ubuntu/v/ubuntu-advantage-tools/focal?label=Focal&logo=ubuntu&logoColor=white)
![Released Jammy Version](https://img.shields.io/ubuntu/v/ubuntu-advantage-tools/jammy?label=Jammy&logo=ubuntu&logoColor=white)

The Ubuntu Pro Client (`pro`) is the official tool to enable Canonical offerings on your
system.

`pro` provides support to view, enable, and disable the following Canonical services:

- [Common Criteria EAL2 Certification Tooling](https://ubuntu.com/security/cc)
- [CIS Benchmark Audit Tooling](https://ubuntu.com/security/cis)
- [Ubuntu Security Guide (USG) Tooling](https://ubuntu.com/security/certifications/docs/usg)
- [Ubuntu Expanded Security Maintenance (ESM)](https://ubuntu.com/security/esm)
- [Robot Operating System (ROS) Expanded Security Maintenance](https://ubuntu.com/robotics/ros-esm)
- [FIPS 140-2 Certified Modules (and optional non-certified patches)](https://ubuntu.com/security/fips)
- [Livepatch Service](https://ubuntu.com/security/livepatch)


If you need any of those services for your machine, `pro` is the right tool for you.

`pro` is already installed on every Ubuntu system. Try it out by running `pro help`!

## Documentation

### Tutorials

* [Getting started with Ubuntu Pro Client](./docs/tutorials/basic_commands.md)
* [Create a FIPS compliant Ubuntu Docker image](./docs/tutorials/create_a_fips_docker_image.md)
* [Fix vulnerabilities by CVE or USN using `pro fix`](./docs/tutorials/fix_scenarios.md)
* [Create a Custom Ubuntu Pro Cloud Image with FIPS Updates](./docs/tutorials/create_a_fips_updates_pro_cloud_image.md)

### How To Guides

* [How to get an Ubuntu Pro token and attach to a subscription](./docs/howtoguides/get_token_and_attach.md)
* [How to Configure Proxies](./docs/howtoguides/configure_proxies.md)
* [How to Enable Ubuntu Pro Services in a Dockerfile](./docs/howtoguides/enable_in_dockerfile.md)
* [How to Create a custom Golden Image based on Public Cloud Ubuntu Pro images](./docs/howtoguides/create_pro_golden_image.md)
* [How to Manually update MOTD and APT messages](./docs/howtoguides/update_motd_messages.md)
* [How to enable CIS](./docs/howtoguides/enable_cis.md)
* [How to enable CC EAL](./docs/howtoguides/enable_cc.md)
* [How to enable ESM Infra](./docs/howtoguides/enable_esm_infra.md)
* [How to enable FIPS](./docs/howtoguides/enable_fips.md)
* [How to enable Livepatch](./docs/howtoguides/enable_livepatch.md)
* [How to configure a timer job](./docs/howtoguides/configuring_timer_jobs.md)
* [How to attach with a configuration file](./docs/howtoguides/how_to_attach_with_config_file.md)
* [How to collect Ubuntu Pro Client logs](./docs/howtoguides/how_to_collect_logs.md)
* [How to simulate attach operation](./docs/howtoguides/how_to_simulate_attach.md)
* [How to run `pro fix` in dry-run mode](./docs/howtoguides/how_to_run_fix_in_dry_run_mode.md)

### Reference

* [Ubuntu Release and Architecture Support Matrix](./docs/references/support_matrix.md)
* [Network Requirements](./docs/references/network_requirements.md)
* [API Reference Guide](./docs/references/api.md)
* [PPAs with different versions of `pro`](./docs/references/ppas.md)

### Explanation

* [What is the daemon for? (And how to disable it)](./docs/explanations/what_is_the_daemon.md)
* [What are Public Cloud Ubuntu Pro instances?](./docs/explanations/what_are_ubuntu_pro_cloud_instances.md)
* [What is the ubuntu-advantage-pro package?](./docs/explanations/what_is_the_ubuntu_advantage_pro_package.md)
* [What are the timer jobs?](./docs/explanations/what_are_the_timer_jobs.md)
* [What are the Ubuntu Pro related MOTD messages?](./docs/explanations/motd_messages.md)
* [What are the Ubuntu Pro related APT messages?](./docs/explanations/apt_messages.md)
* [How to interpret the security-status command](./docs/explanations/how_to_interpret_the_security_status_command.md)
* [Why Trusty (14.04) is no longer supported](./docs/explanations/why_trusty_is_no_longer_supported.md)

## Project and community

Ubuntu Pro Client is a member of the Ubuntu family. It’s an open source project that warmly welcomes
community projects, contributions, suggestions, fixes and constructive feedback.

* [Contribute](CONTRIBUTING.md)
