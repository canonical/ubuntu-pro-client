@suite_feature_hook
Feature: flaky scenario next to a feature whose hook fails

  Scenario: fails once and then passes
    Given the step fails once for key "feature_hook"
