@uses.config.contract_token
Feature: Enable command behaviour when attached to an Ubuntu Pro subscription

  # Overall test for overrides; in the future, when many services
  # have overrides, we can consider removing this
  # esm-infra is a good choice because it doesn't already have
  # other overrides that would interfere with the test
  Scenario: Cloud overrides for a generic aws Focal instance
    Given a `focal` `aws.generic` machine with ubuntu-advantage-tools installed
    When I set the machine token overlay to the following yaml
      """
      machineTokenInfo:
        contractInfo:
          resourceEntitlements:
            - type: esm-infra
              overrides:
                - selector:
                    series: focal
                  directives:
                    additionalPackages:
                      - some-package-focal
                - selector:
                    cloud: aws
                  directives:
                    additionalPackages:
                      - some-package-aws
      """
    And I attach `contract_token` with sudo and options `--no-auto-enable`
    And I verify that running `pro enable esm-infra` `with sudo` exits `1`
    Then stdout matches regexp:
      """
      E: Unable to locate package some-package-aws
      """
