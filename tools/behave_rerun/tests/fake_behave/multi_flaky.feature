@suite_multi_flaky
Feature: multiple flaky examples

  Scenario Outline: each example fails once
    Given the step fails once for key "<key>"

    Examples: values
      | key   |
      | one   |
      | two   |
      | three |
