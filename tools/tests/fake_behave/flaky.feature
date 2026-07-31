@suite_flaky
Feature: flaky suite

  Scenario: fails once and then passes
    Given the step fails once for key "single"
