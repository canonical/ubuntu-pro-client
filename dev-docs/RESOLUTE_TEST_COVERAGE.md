# Resolute Feature Test Coverage

## INSTRUCTIONS FOR AGENTS

Agents like Copilot, Claude, and Gemini should treat this section like a skill. They must follow the steps outlined here:

1. Iterate through the tests scenarios in the file
2. Summarize the scenario for the user
3. Ask the user if Resolute should be added for the scenario. List the distributions that the scenario currently uses. Make a recommendation based on the test logic and the current releases tested.
4. If present, drop Plucky for the scenario
5. Run tests and see output.
6. If tests failed, pause and ask me to run the test scenario for Resolute using the archive release. Mark the correct command to run, including the test file name, the machine types, and any additional config that is required.
7. Mark the update status on the scenario (added resolute, partially updated, skipped) in the "Tests Evaluated" section. Remove it from the "Tests Pending Evaluation" section.
8. If a test is not updated, mark it as "skipped" and note why.

IMPORTANT: after each test file, you MUST pause and wait for explicit instructions to continue.

Example command for a test:

```sh
export UACLIENT_BEHAVE_CONTRACT_TOKEN=C13o39iWs2AogUCgFnDGvX4a2rAZ8Y
UACLIENT_BEHAVE_INSTALL_FROM=local tox -e behave -- features/cli/help.feature -D releases=resolute -D machine_types=lxd-container &> tmpresults.txt
```

When running a test, ALWAYS push the output into a temp file so that you can inspect failures. The tempfile may be in the repo or in `/tmp`.

Only test lxd containers and VMs. Do not test clouds or WSL.

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

## Tests Pending Evaluation

- features/cli/collect_logs.feature
- features/cli/config.feature
- features/cli/cve.feature
- features/cli/cves.feature
- features/cli/detach.feature
- features/cli/disable.feature
- features/cli/enable.feature
- features/cli/magic_attach.feature
- features/cli/refresh.feature
- features/cli/security_status.feature
- features/cli/status.feature
