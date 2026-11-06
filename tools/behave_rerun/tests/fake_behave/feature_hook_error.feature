@suite_feature_hook @before_feature_fails_once
Feature: feature hook that fails once

  Scenario: fails whenever it runs
    Given the step always fails
