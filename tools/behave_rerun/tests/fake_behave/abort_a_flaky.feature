@suite_abort
Feature: flaky scenario before an abort

  Scenario: fails once and then passes
    Given the step fails once for key "abort_flaky"
