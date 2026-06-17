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

- detached_auto_attach.feature
- docker.feature
- enable_fips_cloud.feature
- enable_fips_container.feature
- enable_fips_pro.feature
- enable_fips_vm.feature
- esm.feature
- esm_cache.feature
- fix.feature
- i18n.feature
- install_uninstall.feature
- landscape.feature
- legacy.feature
- livepatch.feature
- logs.feature
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
