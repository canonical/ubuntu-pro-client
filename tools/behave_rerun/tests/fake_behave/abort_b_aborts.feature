@suite_abort
Feature: scenario hook that aborts the run once

  @aborts_once
  Scenario: aborts before its steps the first time
    Given the step passes
