Feature: u.pro.services.dependencies

  Scenario Outline: u.pro.services.dependencies.v1
    Given a `<release>` `<machine_type>` machine with ubuntu-advantage-tools installed
    When I run `pro api u.pro.services.dependencies.v1` as non-root
    Then API data field output is:
      """
      {
        "attributes": {
          "services": [
            {
              "depends_on": [],
              "incompatible_with": [],
              "name": "anbox-cloud"
            },
            {
              "depends_on": [],
              "incompatible_with": [],
              "name": "cc-eal"
            },
            {
              "depends_on": [],
              "incompatible_with": [],
              "name": "cis"
            },
            {
              "depends_on": [],
              "incompatible_with": [],
              "name": "esm-apps"
            },
            {
              "depends_on": [],
              "incompatible_with": [],
              "name": "esm-infra"
            },
            {
              "depends_on": [],
              "incompatible_with": [
                {
                  "name": "livepatch",
                  "reason": {
                    "code": "livepatch-invalidates-fips",
                    "title": "Livepatch cannot be enabled while running the official FIPS certified kernel. If you would like a FIPS compliant kernel with additional bug fixes and security updates, you can use the FIPS Updates service with Livepatch."
                  }
                },
                {
                  "name": "fips-updates",
                  "reason": {
                    "code": "fips-updates-invalidates-fips",
                    "title": "FIPS cannot be enabled if FIPS Updates has ever been enabled because FIPS Updates installs security patches that aren't officially certified."
                  }
                },
                {
                  "name": "realtime-kernel",
                  "reason": {
                    "code": "realtime-fips-incompatible",
                    "title": "Realtime and FIPS require different kernels, so you cannot enable both at the same time."
                  }
                }
              ],
              "name": "fips"
            },
            {
              "depends_on": [],
              "incompatible_with": [
                {
                  "name": "fips",
                  "reason": {
                    "code": "fips-invalidates-fips-updates",
                    "title": "FIPS Updates cannot be enabled if FIPS is enabled. FIPS Updates installs security patches that aren't officially certified."
                  }
                },
                {
                  "name": "realtime-kernel",
                  "reason": {
                    "code": "realtime-fips-updates-incompatible",
                    "title": "Realtime and FIPS Updates require different kernels, so you cannot enable both at the same time."
                  }
                }
              ],
              "name": "fips-updates"
            },
            {
              "depends_on": [],
              "incompatible_with": [
                {
                  "name": "livepatch",
                  "reason": {
                    "code": "livepatch-invalidates-fips",
                    "title": "Livepatch cannot be enabled while running the official FIPS certified kernel. If you would like a FIPS compliant kernel with additional bug fixes and security updates, you can use the FIPS Updates service with Livepatch."
                  }
                },
                {
                  "name": "fips-updates",
                  "reason": {
                    "code": "fips-updates-invalidates-fips",
                    "title": "FIPS cannot be enabled if FIPS Updates has ever been enabled because FIPS Updates installs security patches that aren't officially certified."
                  }
                },
                {
                  "name": "realtime-kernel",
                  "reason": {
                    "code": "realtime-fips-incompatible",
                    "title": "Realtime and FIPS require different kernels, so you cannot enable both at the same time."
                  }
                },
                {
                  "name": "fips",
                  "reason": {
                    "code": "fips-invalidates-fips-updates",
                    "title": "FIPS Updates cannot be enabled if FIPS is enabled. FIPS Updates installs security patches that aren't officially certified."
                  }
                }
              ],
              "name": "fips-preview"
            },
            {
              "depends_on": [],
              "incompatible_with": [],
              "name": "landscape"
            },
            {
              "depends_on": [],
              "incompatible_with": [
                {
                  "name": "fips",
                  "reason": {
                    "code": "livepatch-invalidates-fips",
                    "title": "Livepatch cannot be enabled while running the official FIPS certified kernel. If you would like a FIPS compliant kernel with additional bug fixes and security updates, you can use the FIPS Updates service with Livepatch."
                  }
                },
                {
                  "name": "realtime-kernel",
                  "reason": {
                    "code": "realtime-livepatch-incompatible",
                    "title": "Livepatch does not currently cover the Real-time kernel."
                  }
                }
              ],
              "name": "livepatch"
            },
            {
              "depends_on": [],
              "incompatible_with": [
                {
                  "name": "fips",
                  "reason": {
                    "code": "realtime-fips-incompatible",
                    "title": "Realtime and FIPS require different kernels, so you cannot enable both at the same time."
                  }
                },
                {
                  "name": "fips-updates",
                  "reason": {
                    "code": "realtime-fips-updates-incompatible",
                    "title": "Realtime and FIPS Updates require different kernels, so you cannot enable both at the same time."
                  }
                },
                {
                  "name": "livepatch",
                  "reason": {
                    "code": "realtime-livepatch-incompatible",
                    "title": "Livepatch does not currently cover the Real-time kernel."
                  }
                }
              ],
              "name": "realtime-kernel"
            },
            {
              "depends_on": [
                {
                  "name": "esm-infra",
                  "reason": {
                    "code": "ros-requires-esm",
                    "title": "ROS packages assume ESM updates are enabled."
                  }
                },
                {
                  "name": "esm-apps",
                  "reason": {
                    "code": "ros-requires-esm",
                    "title": "ROS packages assume ESM updates are enabled."
                  }
                }
              ],
              "incompatible_with": [],
              "name": "ros"
            },
            {
              "depends_on": [
                {
                  "name": "esm-infra",
                  "reason": {
                    "code": "ros-requires-esm",
                    "title": "ROS packages assume ESM updates are enabled."
                  }
                },
                {
                  "name": "esm-apps",
                  "reason": {
                    "code": "ros-requires-esm",
                    "title": "ROS packages assume ESM updates are enabled."
                  }
                },
                {
                  "name": "ros",
                  "reason": {
                    "code": "ros-updates-requires-ros",
                    "title": "ROS bug-fix updates assume ROS security fix updates are enabled."
                  }
                }
              ],
              "incompatible_with": [],
              "name": "ros-updates"
            }
          ]
        },
        "meta": {
          "environment_vars": []
        },
        "type": "ServiceDependencies"
      }
      """
    When I create the file `/tmp/dependencies.py` with the following:
      """
      import yaml
      from uaclient.api.u.pro.services.dependencies.v1 import dependencies

      print(yaml.dump(dependencies().to_dict(), default_flow_style=False))
      """
    And I run `python3 /tmp/dependencies.py` with sudo
    Then I will see the following on stdout:
      """
      services:
      - depends_on: []
        incompatible_with: []
        name: anbox-cloud
      - depends_on: []
        incompatible_with: []
        name: cc-eal
      - depends_on: []
        incompatible_with: []
        name: cis
      - depends_on: []
        incompatible_with: []
        name: esm-apps
      - depends_on: []
        incompatible_with: []
        name: esm-infra
      - depends_on: []
        incompatible_with:
        - name: livepatch
          reason:
            code: livepatch-invalidates-fips
            title: Livepatch cannot be enabled while running the official FIPS certified
              kernel. If you would like a FIPS compliant kernel with additional bug fixes
              and security updates, you can use the FIPS Updates service with Livepatch.
        - name: fips-updates
          reason:
            code: fips-updates-invalidates-fips
            title: FIPS cannot be enabled if FIPS Updates has ever been enabled because
              FIPS Updates installs security patches that aren't officially certified.
        - name: realtime-kernel
          reason:
            code: realtime-fips-incompatible
            title: Realtime and FIPS require different kernels, so you cannot enable both
              at the same time.
        name: fips
      - depends_on: []
        incompatible_with:
        - name: fips
          reason:
            code: fips-invalidates-fips-updates
            title: FIPS Updates cannot be enabled if FIPS is enabled. FIPS Updates installs
              security patches that aren't officially certified.
        - name: realtime-kernel
          reason:
            code: realtime-fips-updates-incompatible
            title: Realtime and FIPS Updates require different kernels, so you cannot enable
              both at the same time.
        name: fips-updates
      - depends_on: []
        incompatible_with:
        - name: livepatch
          reason:
            code: livepatch-invalidates-fips
            title: Livepatch cannot be enabled while running the official FIPS certified
              kernel. If you would like a FIPS compliant kernel with additional bug fixes
              and security updates, you can use the FIPS Updates service with Livepatch.
        - name: fips-updates
          reason:
            code: fips-updates-invalidates-fips
            title: FIPS cannot be enabled if FIPS Updates has ever been enabled because
              FIPS Updates installs security patches that aren't officially certified.
        - name: realtime-kernel
          reason:
            code: realtime-fips-incompatible
            title: Realtime and FIPS require different kernels, so you cannot enable both
              at the same time.
        - name: fips
          reason:
            code: fips-invalidates-fips-updates
            title: FIPS Updates cannot be enabled if FIPS is enabled. FIPS Updates installs
              security patches that aren't officially certified.
        name: fips-preview
      - depends_on: []
        incompatible_with: []
        name: landscape
      - depends_on: []
        incompatible_with:
        - name: fips
          reason:
            code: livepatch-invalidates-fips
            title: Livepatch cannot be enabled while running the official FIPS certified
              kernel. If you would like a FIPS compliant kernel with additional bug fixes
              and security updates, you can use the FIPS Updates service with Livepatch.
        - name: realtime-kernel
          reason:
            code: realtime-livepatch-incompatible
            title: Livepatch does not currently cover the Real-time kernel.
        name: livepatch
      - depends_on: []
        incompatible_with:
        - name: fips
          reason:
            code: realtime-fips-incompatible
            title: Realtime and FIPS require different kernels, so you cannot enable both
              at the same time.
        - name: fips-updates
          reason:
            code: realtime-fips-updates-incompatible
            title: Realtime and FIPS Updates require different kernels, so you cannot enable
              both at the same time.
        - name: livepatch
          reason:
            code: realtime-livepatch-incompatible
            title: Livepatch does not currently cover the Real-time kernel.
        name: realtime-kernel
      - depends_on:
        - name: esm-infra
          reason:
            code: ros-requires-esm
            title: ROS packages assume ESM updates are enabled.
        - name: esm-apps
          reason:
            code: ros-requires-esm
            title: ROS packages assume ESM updates are enabled.
        incompatible_with: []
        name: ros
      - depends_on:
        - name: esm-infra
          reason:
            code: ros-requires-esm
            title: ROS packages assume ESM updates are enabled.
        - name: esm-apps
          reason:
            code: ros-requires-esm
            title: ROS packages assume ESM updates are enabled.
        - name: ros
          reason:
            code: ros-updates-requires-ros
            title: ROS bug-fix updates assume ROS security fix updates are enabled.
        incompatible_with: []
        name: ros-updates
      """

    Examples: ubuntu release
      | release | machine_type  |
      | xenial  | lxd-container |
      | bionic  | lxd-container |
      | focal   | lxd-container |
      | jammy   | lxd-container |
      | mantic  | lxd-container |
