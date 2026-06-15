# Resolute Feature Test Coverage

**Date:** 2026-06-15  
**Goal:** Systematically evaluate feature tests and determine which should include resolute (26.04) in their run list.

---

## Test Evaluation Summary

### ✅ Tests Updated with Resolute

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

---

### ⏭️ Tests Skipped (Not Updated)

#### `airgapped.feature`

- **Status:** ⏭️ Skipped
- **Current Releases:** jammy only
- **Reason:** Mirror and contracts setup are hardcoded to jammy. APT output assertions check for `jammy-apps-security/main`. Would require significant rework to support new releases.
- **Action:** Revisit after mirror infrastructure supports resolute.

---

### 🔄 Tests Under Evaluation

#### `apt_messages.feature`

- **Current Releases:** Complex — varies by scenario
  - Scenario 1 (APT JSON Hook on xenial): xenial only
  - Scenario 2 (APT Hook advertises esm-infra): xenial, bionic, focal
  - Scenario 3 (APT Hook advertises esm-apps): jammy (TODO comment suggests noble needs esm package)
  - Scenario 4 (APT News): xenial, bionic, focal, jammy, noble
  - Scenario 5 (APT News plucky variant): plucky, questing
  - Scenario 6 (Cloud and series-specific URLs): Multiple release × cloud combinations
  - Scenario 7-10 (APT news selectors & edge cases): Various
- **Outstanding Question:** How should we handle this large, multi-scenario file? Add resolute everywhere questing appears, or is deeper review needed?
- **Status:** Awaiting user guidance

---

### 📋 Tests Pending Evaluation

- autocomplete.feature
- cc_eal.feature
- cis.feature
- cloud_pro_clone.feature
- contract_expired.feature
- daemon.feature
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
