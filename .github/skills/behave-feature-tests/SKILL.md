---
name: behave-feature-tests
description: Run and troubleshoot Ubuntu Pro Client Behave feature tests, found in the `features/` directory.
---

# Behave Feature Tests

TODO: add context about how behave tests run

## Adding new Examples

When editing the `Examples` matrix, the existing precedent is the most important reference. Updating the `Examples` should not require any changes to the test body. If it does, you MUST raise this concern to the user. You MUST NOT edit the body of a test without consent from the user.

Before adding to the `Examples`, you MUST decide if the example is relevant to the test. The most common update to `Examples` is adding a new release, either an LTS or a non-LTS.

Examples MUST be ordered by release, based on the release year. For example:

```
    Examples: version
      | release  | machine_type   |
      | xenial   | lxd-container  |
      | xenial   | lxd-vm         |
      | bionic   | lxd-container  |
      | bionic   | lxd-vm         |
      | focal    | lxd-container  |
      | focal    | lxd-vm         |
      | jammy    | lxd-container  |
      | jammy    | lxd-vm         |
      | noble    | lxd-container  |
      | noble    | lxd-vm         |
      | questing | lxd-container  |
      | questing | lxd-vm         |
      | resolute | lxd-container  |
      | resolute | lxd-vm         |
      | stonking | lxd-container  |
      | stonking | lxd-vm         |
```

After adding a new example, you MUST validate the change by running the test to ensure it passes.

### Adding a non-LTS

Non-LTS releases (plucky, questing, stonking, etc.) generally have limited functionality. They might not be valid for every scenario. If the last non-LTS is present in a test, then the next non-LTS should be present.

For example, if `plucky` (25.04) is present, then `questing` (25.10) is a good candidate. If `questing` (25.10) is present, then `stonking` (26.10) is a good candidate.

Supported features change, so these are not hard rules.

### Adding an LTS

LTS releases come out on two year boundaries.

LTS releases are:

- Xenial (16.04)
- Bionic (18.04)
- Focal (20.04)
- Jammy (22.04)
- Noble (24.04)
- Resolute (26.04)

If the last LTS is present in a scenario, then the next LTS is a good candidate. For example, if `noble` (24.04) is present, then `resolute` (26.04) is a good candidate.

Some features are only applicable to older releases. If a release is skipped, you may assume that the feature is no longer applicable to subsequent releases. E.g., if the current release is Resolute 26.04, and the last scenario in a test was for Jammy 22.04, you may assume that the feature was not applicable to Noble and is therefore not applicable to Resolute.

## Using the MCP

You SHOULD run tests using the behave MCP server if available. If the MCP server is unavailable or cannot run a particular test, you MUST raise this concern to the user before attempting to do anything else.

TODO: add note to the MCP about local builds/upstream builds

## Diagnosing test failures

You SHOULD attempt to identify if a test failure is due to a true failure in the Ubuntu Pro client or if the failure is  due to a faulty test harness.

## Pitfalls

- You SHOULD use the git hook run `reformat-gherkin`; you SHOULD NOT reformat feature files by hand unless specifically requested. You SHOULD add the autoformatted changes and attempt the commit again.
