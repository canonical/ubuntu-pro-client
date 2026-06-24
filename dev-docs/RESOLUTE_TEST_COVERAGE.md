# Resolute Feature Test Coverage

## INSTRUCTIONS FOR AGENTS

Agents like Copilot, Claude, and Gemini should treat this section like a skill. They must follow the steps outlined here:

1. Iterate through the tests scenarios in the file
2. Summarize the scenario for the user
3. Ask the user if Resolute should be added for the scenario. List the distributions that the scenario currently uses. Make a recommendation based on the test logic and the current releases tested.
4. If present, drop Plucky for the scenario
5. Give user command to run tests locally
6. Mark the update status on the scenario (added resolute, partially updated, skipped) in the "Tests Evaluated" section. Remove it from the "Tests Pending Evaluation" section.
7. If a test is not updated, mark it as "skipped" and note why. We will make follow up tickets for any failures, so we want to be able to aggregate related failures in our tickets. Those tickets will need to update these tests as part of the fix.

IMPORTANT: after each test file, you MUST pause and wait for explicit instructions to continue.
IMPORTANT: after each confirmed test pass/fail, you must update this test tracker.
IMPORTANT: you must structure your example test commands exactly like so, replacing only the tests under investigation:

```sh
export UACLIENT_BEHAVE_CONTRACT_TOKEN=C13o39iWs2AogUCgFnDGvX4a2rAZ8Y
UACLIENT_BEHAVE_INSTALL_FROM=local tox -e behave -- features/cli/help.feature -D releases=resolute -D machine_types=lxd-container,lxd-vm &> docs/tmpresults_help.txt
```

Only test lxd containers and VMs. Do not test clouds or WSL.

DO NOT MAKE COMMITS. I will commit things.

A scenario is a good candidate for resolute if it already runs on noble, plucky, or questing.
If not updating a scenario in a test, explicitly note why, e.g., "hardcoded logic for jammy", or "only runs on Xenial".

IMPORTANT: Resolute is 26.04 LTS. It comes after Questing, 25.10, in ordered lists. It also comes after Noble 24.04 LTS.

## Decision Categories

| Category | Action | Examples |
|----------|--------|----------|
| **Generic tests** | Add resolute following questing pattern | _version.feature |
| **Release-upgrade tests** | Update upgrade chains; may need questing→resolute path | ubuntu_upgrade.feature |
| **Service-dependent** | Check service support before adding | anbox.feature, docker.feature |
| **Hardcoded values** | Requires rework; skip unless critical | airgapped.feature |
| **Legacy/deprecated** | Skip or deprecate | legacy.feature, ros.feature |

## Tests Evaluated

- features/cli/help.feature
  - Status: partially updated
  - Current releases: xenial, bionic, focal, jammy, noble, questing, resolute
  - Update: dropped plucky and added resolute in all three release example tables

- features/cli/attach.feature
  - Status: partially updated
  - Current releases: xenial, bionic, focal, jammy, noble, questing, resolute
  - Update applied:
    - Retained LTS+resolute coverage for all container/vm scenarios (attached command, attach config, json output, contract change, invalid/expired token, lxd-vm)
    - Switched non-LTS spot check from plucky to questing in "Attached command in a non-lts ubuntu machine" scenario
    - Removed untested resolute cloud rows from "Attach command in generic cloud images" per policy
  - Skipped LXD VM: https://warthogs.atlassian.net/browse/UPRO-1218

- features/cli/auto_attach.feature
  - Status: updated
  - Current releases: xenial, bionic, focal, jammy, noble, questing, resolute
  - Update applied:
    - Replaced plucky with resolute in both scenario example tables.
    - Kept questing coverage unchanged.

- features/cli/collect_logs.feature
  - Status: updated
  - Current releases: xenial, bionic, focal, jammy, noble, questing, resolute
  - Update applied:
    - Replaced plucky with resolute in the unattached-machine scenario table.
    - Added resolute to the attached-machine scenario table.

- features/cli/config.feature
  - Status: updated
  - Current releases: xenial, jammy, noble, questing, resolute
  - Update applied:
    - Replaced plucky with resolute in the scenario table.
    - Updated release-specific stderr assertion branch from plucky to resolute.

- features/cli/cve.feature
  - Status: skipped
  - Current releases: xenial, focal
  - Reason:
    - Scenarios are hardcoded to xenial/focal fixtures and assertions (including explicit Ubuntu 16.04 messaging), so this file is not a safe generic resolute-add candidate without reworking test data and expectations.

- features/cli/cves.feature
  - Status: skipped
  - Current releases: xenial, jammy
  - Reason:
    - Scenarios are hardcoded to release-specific fixture data and metadata endpoints (`com.ubuntu.xenial.pkg.json.xz` and `com.ubuntu.jammy.pkg.json.xz`), so adding resolute safely requires fixture and expectation rework.

- features/cli/detach.feature
  - Status: updated
  - Current releases: xenial, bionic, focal, jammy, noble, questing, resolute
  - Update applied:
    - Added resolute lxd-container rows in both scenario tables.
    - Dropped plucky from the unattached-detach scenario table.
    - Left existing WSL rows unchanged.

- features/cli/disable.feature
  - Status: updated
  - Current releases: xenial, bionic, focal, jammy, noble, questing, resolute
  - Update applied:
    - Added resolute to attached and unattached lxd-container scenario tables and dropped plucky from unattached.
    - Commented out resolute row in the attached unknown-service/wrong-output-format scenario with TODO(UPRO-1225): re-enable once ua-contracts CIS `presentedAs` behavior matches noble.
    - https://warthogs.atlassian.net/browse/UPRO-1225
    - Removed resolute row from "Disable with purge works and purges repo services not involving a kernel" with TODO: ansible is not present from esm-apps on resolute and scenario likely needs refactor.
    - Removed resolute row from "Disable with purge unsupported services" with TODO(UPRO-1218): re-enable after AppArmor fix.
    - Kept slow FIPS kernel-purge scenarios unchanged (xenial/bionic/focal only).
    - https://warthogs.atlassian.net/browse/UPRO-1218

- features/cli/enable.feature
  - Status: updated
  - Current releases: xenial, bionic, focal, jammy, noble, questing, resolute
  - Update applied:
    - Added resolute to generic LXD release tables that previously ended at noble: reboot-required, empty-series-affordance, attached JSON enable, not-entitled, corrupt-lock, and both `pro enable --auto` scenario outlines.
    - Updated unattached table by dropping plucky and adding resolute after questing.
    - Left cloud override scenario unchanged (aws-specific focal test).
    - Left legacy narrow-scope tables unchanged where release coverage is intentionally constrained.
    - https://warthogs.atlassian.net/browse/UPRO-1225

- features/cli/magic_attach.feature
  - Status: updated
  - Current releases: xenial, bionic, focal, jammy, noble, resolute
  - Update applied:
    - Added resolute to the single release example table for the magic attach flow scenario.

- features/cli/refresh.feature
  - Status: updated
  - Current releases: xenial, bionic, focal, jammy, noble, questing, resolute
  - Update applied:
    - Added resolute lxd-container rows in both scenario tables.
    - Dropped plucky from both scenario tables.
    - Left existing WSL rows unchanged.

- features/cli/security_status.feature
  - Status: skipped
  - Current releases: xenial, bionic, focal, noble, questing
  - Update applied:
    - Swapped plucky -> questing in the dedicated latest non-LTS scenario table.
  - Reason:
    - Most scenarios are release-specific (xenial/bionic/focal/plucky behavior and package/version-pinned assertions), so broad resolute addition is not a safe generic update without substantial fixture/expectation rework.

- features/cli/status.feature
  - Status: updated
  - Current releases: xenial, bionic, focal, jammy, noble, questing, resolute
  - Update applied:
    - Updated generic multi-release tables by dropping plucky and adding resolute.
    - Updated "Attached status in the latest LTS ubuntu machine" scenario to use resolute with correct output: short view shows anbox-cloud, esm-apps, esm-infra, landscape; --all view includes cis, fips/fips-preview/fips-updates/realtime-kernel/ros/ros-updates all as n/a (no usg, no realtime-kernel subtrees).
    - Added "Attached status in the latest LTS ubuntu machine - resolute" as an explicit resolute-specific scenario documenting the early service baseline.
    - Added "Unattached status in a ubuntu machine - resolute" scenario with correct available/unavailable service list for resolute (cis/fips-updates/realtime-kernel/ros/ros-updates all present but unavailable).
  - Note: Resolute's short status omits services that are n/a (fips-updates, usg/cis, realtime-kernel, ros). The --all view shows the full list. As ua-contracts adds CIS/FIPS/ROS support for resolute, these scenarios should be updated.

## Tests Pending Evaluation

- None
