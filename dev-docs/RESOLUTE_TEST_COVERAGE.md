# Resolute Feature Test Coverage

**Date:** 2026-06-15  
**Goal:** Systematically evaluate feature tests and determine which should include resolute (26.04) in their run list.

---

## INSTRUCTIONS FOR AGENTS

Agents like Copilot, Claude, and Gemini should treat this section like a skill. They must follow the steps outlined here:

1. Iterate through the tests scenarios in the file
2. Summarize the scenario for the user
3. Ask the user if Resolute should be added for the scenario. List the distributions that the scenario currently uses.
4. If present, drop Plucky for the scenario
5. Run the test scenario for Resolute using the archive release
6. Mark the update status on the scenario (added resolute, partially updated, skipped) in the "Tests Evaluated" section. Remove it from the "Tests Pending Evaluation" section.
7. If a test is not updated, mark it as "skipped" and note why.

How to run a test:

```sh
UACLIENT_BEHAVE_INSTALL_FROM=local tox -e behave -- features/airgapped.feature -D releases=resolute -D machine_types=lxd-container
```

Some tests require a token. I will export into the terminal so that you may use it.

IMPORTANT: after each test file, you MUST pause and wait for explicit instructions to continue.

## Test Evaluation Summary

### ✅ Tests Evaluated

#### `_version.feature`

- **Status:** ✅ Added resolute
- **Scenarios Updated:** 4
  1. "Check pro version" — all machine types (lxd-container, lxd-vm, aws.generic, azure.generic, gcp.generic)
  2. "Check pro version @upgrade" — lxd-container
  3. "Attached show version" — lxd-container
  4. "Check for newer versions @arm64" — lxd-container
- **Reason:** Generic version-check test with no release-specific logic. Follows same pattern as questing.

#### `anbox.feature`

- **Status:** ✅ Added resolute
- **Scenarios Updated:** 2
  1. "Enable Anbox cloud service in a container" — all machine types (lxd-container, lxd-vm)
  2. "Enable Anbox cloud service in a VM" — lxd-container, lxd-vm
- **Reason:** Anbox Cloud APT archive URL is parameterized; supports new releases seamlessly.

#### `apt_messages.feature`

- **Status:** ✅ Partially updated; drops applied
- **Scenarios Updated:**
  1. "APT Hook advertises esm-infra on upgrade" — resolute removed; this test only applies to EOL releases where esm-infra is meaningful
  2. "APT Hook advertises esm-apps on upgrade" — resolute commented out with TODO; needs esm packages with higher version than archives for both noble and resolute
  3. "APT News" (old output format, full-range) — added resolute
  4. "APT News" (new output format, questing+) — dropped plucky; added resolute
  5. "APT news selectors" (old output format) — kept xenial through noble; moved resolute to scenario 6
  6. "APT news selectors" (new output format) — replaced plucky with resolute (noble→resolute wrong_release)
  7. "APT Hook does not error when run as non-root" — dropped plucky; added resolute
  8. "APT Hook do not advertises esm-apps on upgrade for interim releases" — dropped plucky; kept questing
- **Scenarios Unchanged:**
  1. "APT JSON Hook on xenial" — xenial-only legacy test; kept as-is
  2. "Cloud and series-specific URLs" — hardcoded cloud URLs for legacy releases; kept as-is
- **Drop rationale:** plucky dropped throughout as it is superseded by questing/resolute for coverage of new APT output format

#### `autocomplete.feature`

- **Status:** ✅ Updated
- **Scenario:** "Verify autocomplete options" — generic tab-completion smoke test, no release-specific logic
- **Added:** resolute (lxd-container)
- **Dropped:** plucky
- **Kept:** bionic, focal, jammy, noble, questing, resolute

#### `airgapped.feature`

- **Status:** ⏭️ Skipped
- **Current Releases:** jammy only
- **Reason:** Mirror and contracts setup are hardcoded to jammy. APT output assertions check for `jammy-apps-security/main`. Would require significant rework to support new releases.
- **Action:** Revisit after mirror infrastructure supports resolute.

#### `cc_eal.feature`

- **Status:** ✅ Updated; tested on resolute ✓
- **Scenario 1 & 2** ("Attached enable CC EAL2", "Enable cc-eal with --access-only") — xenial, bionic only; CC EAL2 is not supported on newer releases; no action taken
- **Scenario 3** ("CC EAL2 not available") — added `resolute | lxd-container | 26.04 LTS | Resolute Raccoon`; dropped plucky
- **Kept:** focal, jammy, noble, questing, resolute

#### `cis.feature`

- **Status:** ⏭️ Skipped
- **Current Releases:** xenial, bionic (Scenario 1); focal (Scenario 2)
- **Reason:** CIS Audit is only available on xenial, bionic, and focal. From focal onward, `pro enable cis` redirects to `usg`. New releases use `usg.feature` instead. No CIS scripts ship for resolute.

#### `cloud_pro_clone.feature`

- **Status:** ⏭️ Skipped
- **Current Releases:** bionic, focal (aws.pro, gcp.pro)
- **Reason:** Tests `fips-updates` golden image cloning on cloud Pro instances. FIPS is not available on resolute.

#### `enable_fips_cloud.feature`

- **Status:** ⏭️ Evaluated; not yet applicable to resolute
- **Decision:** no resolute additions for now
- **Reason:** FIPS is not available on noble/resolute in current cloud matrix, and this feature is explicitly tied to cloud FIPS service/kernel availability by release.
- **Revisit:** when noble/resolute cloud FIPS availability is confirmed, re-evaluate all scenarios in this file.

---

### 🔄 Tests Under Evaluation

(None currently)

---

### 📋 Tests Pending Evaluation

#### `contract_expired.feature`

- **Status:** ⏭️ Skipped
- **Current Releases:** jammy (lxd-container)
- **Reason:** Skipped for now. Revisit to evaluate whether noble and resolute should be added — the test logic (esm-apps, update-motd, expired subscription messages) is generic enough to apply to newer releases.

#### `daemon.feature`

- **Status:** ✅ Updated; tested on resolute ✓. **NOTE: needs testing on cloud instances**
- **Added resolute to:**
  - S1 "cloud-id-shim not installed" — lxd-container (generic check); dropped plucky
  - S3 "daemon runs on gcp generic LTS" — gcp.generic; added `resolute | gcp.generic | ubuntu-pro-client`; added `Then on resolute, systemd status output says memory usage is less than 17 MB`
  - S4 "daemon runs on azure generic LTS" — azure.generic
  - S6 "daemon does not start on non-gcp/azure" — aws.generic; dropped plucky
- **Skipped for resolute:**
  - S2 "cloud-id-shim runs on xenial" — xenial-only; no action
  - S5 "daemon does NOT start on non-LTS gcp/azure" — resolute is LTS, must NOT be here; dropped plucky, kept questing only
  - S7 "daemon does not start on cloud Pro" — older releases only (xenial→focal); no action

#### `detached_auto_attach.feature`

- **Status:** ✅ Updated; **NOTE: needs testing on cloud instances** (all scenarios require aws/azure/gcp.generic)
- **Scenario:** "No detaching on manually attached machine on all clouds" — generic logic; `esm-infra` is available on resolute (LTS)
- **Added:** `resolute | aws.generic`, `resolute | azure.generic`, `resolute | gcp.generic`
- **No plucky to drop** (questing also absent from this file)

#### `docker.feature`

- **Status:** ⏭️ Deferred for rework
- **Decision:** removed resolute rows from Scenario 1 for now
- **Reason:** current test matrix couples host release with cross-series container deb builds (xenial/bionic/focal), which introduces infra dependencies (e.g., legacy sbuild chroots) unrelated to resolute validation
- **Revisit:** rework this feature so resolute coverage does not rely on unavailable legacy chroots or storage-driver-specific docker layer paths; then re-evaluate noble/resolute additions for all three scenarios

#### `enable_fips_container.feature`

- **Status:** ⏭️ Evaluated; not yet applicable to resolute
- **Decision:** no resolute additions for either scenario
- **Reason:** both scenarios are tightly coupled to current FIPS package/source expectations on xenial/bionic/focal container paths; resolute applicability is not established yet.
- **Revisit:** re-evaluate when resolute FIPS availability and package/source expectations for container flows are confirmed.

#### `enable_fips_pro.feature`

- **Status:** ⏭️ Evaluated; not yet applicable to resolute
- **Decision:** no resolute additions
- **Reason:** scenario assertions are tied to current PRO-cloud FIPS kernel/package expectations on bionic/focal; resolute applicability is not established yet.
- **Revisit:** re-evaluate when resolute PRO-cloud FIPS availability and expected package/kernel behavior are confirmed.

#### `enable_fips_vm.feature`

- **Status:** ⏭️ Evaluated; not yet applicable to resolute
- **Decision:** no resolute additions for all scenarios in this file
- **Reason:** scenario assertions are tightly coupled to current VM FIPS entitlement/kernel/package behavior (xenial/bionic/focal/jammy matrices, service interactions, and explicit output expectations); resolute applicability is not established yet.
- **Revisit:** re-evaluate once resolute VM FIPS availability and expected behavior/output contracts are confirmed.

#### `esm.feature`

- **Status:** ✅ Partially updated
- **Scenario 1** "enable esm in a machine with -updates disabled" (`/etc/apt/sources.list` path): no resolute addition; kept xenial/bionic/focal/jammy
- **Scenario 2** "enable esm in a machine with -updates disabled" (`/etc/apt/sources.list.d/ubuntu.sources` path): added `resolute | lxd-container`
- **Scenario 3** "esm apt auth includes snapshot urls": added `resolute | lxd-container`
- **Test note:** run skipped in-session per user confirmation of local passing tests

#### `esm_cache.feature`

- **Status:** ✅ Updated
- **Scenario 1** "esm cache failures don't generate errors": added `resolute | lxd-container`
- **Scenario 2** "esm cache failures don't generate errors on xenial" (`@no_gh`): kept xenial-only unchanged
- **Test note:** run skipped in-session per user confirmation of local passing tests

#### `fix.feature`

- **Status:** ✅ Partially updated
- **Scenario 1** "Useful SSL failure message when there aren't any ca-certs": dropped `plucky`; added `resolute | lxd-container`
- **Scenarios 2-6:** kept unchanged (release-specific legacy coverage on focal/xenial/bionic with hardcoded package/version and source-list expectations)
- **Test note:** run skipped in-session per user confirmation of local passing tests

#### `i18n.feature`

- **Status:** ✅ Partially updated
- **Scenario 1** "Translation works" (LTS path): added `resolute | lxd-container`
- **Scenario 2** "Translation works" (non-LTS path): kept non-LTS only; dropped `plucky`, kept `questing`
- **Scenario 3** "Translation doesn't error when python thinks it's ascii only": kept xenial-only unchanged
- **Scenario 4** "apt-hook translations work": kept focal-only unchanged
- **Scenario 5** "Pro client's commands run successfully in a different locale": dropped `plucky`; added `resolute | lxd-container`
- **Scenario 6** "Pro client's commands run successfully in a non-utf8 locale": dropped `plucky`; added `resolute | lxd-container`
- **Test note:** run skipped in-session per user confirmation of local passing tests

#### `install_uninstall.feature`

- **Status:** ⏭️ Evaluated; not applicable to resolute
- **Decision:** no resolute additions
- **Reason:** all 7 scenarios are xenial/bionic only, covering legacy install/uninstall and cloud-init behaviors specific to those older releases
- **Revisit:** no action expected; this file is legacy coverage only

#### `landscape.feature`

- **Status:** ✅ Updated
- **Scenarios 1-3** ("Enable Landscape non-interactively", "Enable Landscape interactively", "Re-enable after disable"): dropped `plucky`; added `resolute | lxd-container`
- **Scenario 2 note:** kept a release guard on the invalid-key stderr assertion for resolute due interactive getpass/prompt output differences on resolute in this test environment
- **Scenario 4** ("Detach/reattach on unsupported release"): jammy-only; no action
- **Scenario 5** ("Landscape inapplicable on unsupported release"): xenial/jammy only; resolute is supported so must not appear here
- **Test note:** run skipped in-session per user confirmation of local passing tests

#### `legacy.feature`

- **Status:** ⏭️ Evaluated; not applicable to resolute
- **Decision:** no resolute additions
- **Reason:** all scenarios are xenial-only and tied to legacy-contract behavior (`contract_token_legacy`, `esm-infra-legacy`, `esm-apps-legacy`)
- **Revisit:** no action expected; this file is legacy coverage only

#### `livepatch.feature`

- **Status:** ✅ Partially updated
- **Scenario 1** "Attached disable of livepatch in a lxd vm": added `resolute | lxd-vm | enabled`
- **Scenario 5** "Livepatch is not enabled by default and can't be enabled on interim releases": dropped `plucky`, kept `questing` (resolute is LTS, so not part of interim-only behavior)
- **Scenarios 2-4 and 6-11:** kept unchanged (targeted focal/jammy/xenial/bionic/wsl/fips/snapd-specific behaviors)
- **Test note:** run skipped in-session per user confirmation of local passing tests

#### `logs.feature`

- **Status:** ✅ Updated
- **Scenarios 1-4** ("The log file can be successfully parsed as json array", "Non-root user and root user log files are different", "Non-root user log files included in collect logs", "logrotate configuration works"): all had identical release matrices (xenial-questing); added `resolute | lxd-container` to all 4; dropped `plucky` from scenarios 2-4
- **Scenario 1 note:** follows noble+ pattern with `user_spec: with sudo` for resolute (matching root-only logging on LTS)
- **Test note:** run skipped in-session per user confirmation of local passing tests

- lxd.feature
- motd_messages.feature
- network_failures.feature
- proxy_config.feature
- realtime_kernel.feature
- reboot_cmds.feature
- retry_auto_attach.feature
- ros.feature
- subscription_attach_restrictions.feature
- timer.feature
- ubuntu_pro.feature
- ubuntu_pro_fips.feature
- ubuntu_upgrade.feature
- ubuntu_upgrade_unattached.feature
- usg.feature
- yaml.feature

---

## Key Observations

1. **Release Pattern**: Tests currently track noble → plucky → questing. Resolute (25.10) comes after questing in the release cycle.
2. **External Dependencies**: Some tests depend on external services (Anbox Cloud, repositories) being ready for new releases.
3. **Hardcoded Values**: Tests with hardcoded release-specific data (pool URLs, version strings, upgrade assertions) require careful review.

---

## Decision Categories

| Category | Action | Examples |
|----------|--------|----------|
| **Generic tests** | Add resolute following questing pattern | _version.feature |
| **Release-upgrade tests** | Update upgrade chains; may need questing→resolute path | ubuntu_upgrade.feature |
| **Service-dependent** | Check service support before adding | anbox.feature, docker.feature |
| **Hardcoded values** | Requires rework; skip unless critical | airgapped.feature |
| **Legacy/deprecated** | Skip or deprecate | legacy.feature, ros.feature |
