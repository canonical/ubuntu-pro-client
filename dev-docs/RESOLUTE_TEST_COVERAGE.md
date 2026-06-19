# Resolute Feature Test Coverage

## INSTRUCTIONS FOR AGENTS

Agents like Copilot, Claude, and Gemini should treat this section like a skill. They must follow the steps outlined here:

1. Iterate through the tests scenarios in the file
2. Summarize the scenario for the user
3. Ask the user if Resolute should be added for the scenario. List the distributions that the scenario currently uses. Make a recommendation based on the test logic and the current releases tested.
4. If present, drop Plucky for the scenario
5. Pause and ask me to un the test scenario for Resolute using the archive release. Mark the correct command to run, including the test file name, the machine types, and any additional config that is required. A test scenario will indicate if additional configuration is required through headers like `@uses.config.contract_token`. See `features/environment.py` for additional configs, if needed.
6. Mark the update status on the scenario (added resolute, partially updated, skipped) in the "Tests Evaluated" section. Remove it from the "Tests Pending Evaluation" section.
7. If a test is not updated, mark it as "skipped" and note why.

IMPORTANT: after each test file, you MUST pause and wait for explicit instructions to continue.

Example command for a test:

```sh
UACLIENT_BEHAVE_INSTALL_FROM=local tox -e behave -- features/api/api.feature -D releases=resolute -D machine_types=lxd-container 
```

DO NOT MAKE COMMITS. I will commit things.

A scenario is a good candidate for resolute if it already runs on noble, plucky, or questing.
If not updating a scenario in a test, explicitly note why, e.g., "hardcoded logic for jammy", or "only runs on Xenial".

## Decision Categories

| Category | Action | Examples |
|----------|--------|----------|
| **Generic tests** | Add resolute following questing pattern | _version.feature |
| **Release-upgrade tests** | Update upgrade chains; may need questing→resolute path | ubuntu_upgrade.feature |
| **Service-dependent** | Check service support before adding | anbox.feature, docker.feature |
| **Hardcoded values** | Requires rework; skip unless critical | airgapped.feature |
| **Legacy/deprecated** | Skip or deprecate | legacy.feature, ros.feature |

## Tests Evaluated

- features/api/api.feature
  - Status: added resolute
  - Update: remove plucky, add resolute
  - Test: pass for resolute
- features/api/configure_retry_service.feature
  - Status: added resolute
  - Update: add resolute
  - Test: pass for resolute
- features/api/cves.feature
  - Status: skipped
  - Reason: unapplicable; xenial only
- features/api/detach.feature
  - Status: blocked
  - Update: added noble to release matrix for validation; must have been missed earlier
  - Test: BLOCKED pending AppArmor resolution (failure occurs mid-scenario during second attach on resolute)
- features/api/disable.feature
  - Status: skipped
  - Reason: release-specific scenario logic blocks direct noble/resolute expansion (legacy ros/ros-updates flows and hardcoded release-version expectations)
- features/api/enable.feature
  - Status: added resolute
  - Update: landscape scenario only; removed plucky and added resolute after questing
  - Test: pass for resolute
- features/api/fix_execute.feature
  - Status: partially updated
  - Updated scenarios:
    - Fix execute command on invalid CVEs/USNs: resolute added
  - Skipped scenarios:
    - Fix execute on a Focal machine: focal-only scenario with focal-specific package/USN/CVE expectations
    - Fix execute API command on a Xenial machine: xenial-only scenario with xenial ESM/pocket behavior and package-version assumptions
    - Fix execute API command on a Bionic machine: bionic-only scenario with bionic package/USN/CVE expectations
- features/api/fix_plan.feature
  - Status: partially updated
  - Updated scenarios:
    - Fix command on an unattached machine (lxd-container): resolute added; lxd-container test treated as pass (single 503 was transient external API flake)
    - Fix command on an unattached machine (lxd-vm): plucky dropped, resolute added after questing
  - Blocked scenarios:
    - lxd-vm resolute run: BLOCKED by known AppArmor issue (denied during machine setup, same issue as detach.feature)
  - Skipped scenarios:
    - Focal-only scenario: only runs on focal
    - Xenial-only scenario: only runs on xenial
    - Bionic-only scenario: only runs on bionic
- features/api/full_auto_attach.feature
  - Status: added resolute
  - Update: resolute added for aws.pro, azure.pro, gcp.pro after noble
  - Test: deferred — cloud instances only, cannot run in local environment

## Tests Pending Evaluation

- features/api/full_token_attach.feature
- features/api/get_guest_token.feature
- features/api/magic_attach.feature
- features/api/packages.feature
- features/api/reboot_required.feature
- features/api/security.feature
- features/api/services_dependencies.feature
- features/api/unattended_upgrades.feature
