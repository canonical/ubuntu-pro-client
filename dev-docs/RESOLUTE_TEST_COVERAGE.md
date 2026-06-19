# Resolute Feature Test Coverage

## INSTRUCTIONS FOR AGENTS

Agents like Copilot, Claude, and Gemini should treat this section like a skill. They must follow the steps outlined here:

1. Iterate through the tests scenarios in the file
2. Summarize the scenario for the user
3. Ask the user if Resolute should be added for the scenario. List the distributions that the scenario currently uses.
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

## Tests Pending Evaluation

- features/api/configure_retry_service.feature
- features/api/cves.feature
- features/api/detach.feature
- features/api/disable.feature
- features/api/enable.feature
- features/api/fix_execute.feature
- features/api/fix_plan.feature
- features/api/full_auto_attach.feature
- features/api/full_token_attach.feature
- features/api/get_guest_token.feature
- features/api/magic_attach.feature
- features/api/packages.feature
- features/api/reboot_required.feature
- features/api/security.feature
- features/api/services_dependencies.feature
- features/api/unattended_upgrades.feature
