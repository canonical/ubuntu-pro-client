@suite_tagged
Feature: tagged suite

  @selected
  Scenario: tagged flaky scenario
    Given the step fails once for key "tagged"

  Scenario: untagged persistent failure
    Given the step always fails
