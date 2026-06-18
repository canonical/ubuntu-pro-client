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

#### `lxd.feature`

- **Status:** ⏭️ Deferred
- **Decision:** remove resolute coverage for now; revisit once AppArmor fix is upstream
- **Reason:** resolute `lxd-vm` runs are currently blocked by AppArmor DENIED in the global behave `after_step` gate before scenario logic executes
- **Revisit note:** when re-enabling resolute coverage, include the scenario-3 host setup fix to install LXD when absent before refresh (`snap list lxd || snap install ...`) because some resolute VM images do not have the `lxd` snap preinstalled

#### `motd_messages.feature`

- **Status:** ✅ Partially updated
- **Scenario 1** "Contract update prevents contract expiration messages": added `resolute | lxd-container | esm-apps`
- **Scenario 2** "Contract Expiration Messages": kept unchanged (xenial/bionic + wsl matrix with `esm-infra` service) to preserve existing release-specific behavior expectations
- **Test note:** run skipped in-session per user confirmation of local passing tests

#### `network_failures.feature`

- **Status:** ✅ Partially updated
- **Scenario 1** "Various HTTP errors are handled gracefully on attaching contract token": added `resolute | lxd-container`
- **Scenario 2** "Network errors for attaching contract token are handled gracefully": added `resolute | lxd-container`
- **Scenario 3** "Network errors for enabling Realtime kernel and Livepatch are handled gracefully": added `resolute | lxd-container | livepatch`; kept resolute `lxd-vm | realtime-kernel` out for now
- **Reason:** generic error-handling coverage on LTS releases; livepatch container path mapped cleanly from noble, but resolute `lxd-vm` realtime-kernel runs currently fail in the global behave AppArmor gate before scenario logic executes
- **Test note:** explicit resolute run attempted; scenarios 1, 2, and livepatch container path passed, while the resolute realtime-kernel VM row hit the same upstream AppArmor blocker seen in `lxd.feature`

#### `proxy_config.feature`

- **Status:** ✅ Partially updated
- **Added resolute to container-backed scenarios:**
  - Scenario 1 "Attach command when proxy is configured for uaclient"
  - Scenario 3 "Attach and config show command when authenticated proxy is configured for uaclient"
  - Scenario 5 "Attach command when proxy is configured globally"
  - Scenario 6 "Attach command when authenticated proxy is configured globally"
  - Scenario 7 "Get warning when configuring global or uaclient proxy"
  - Scenario 8 "apt_http(s)_proxy still works"
- **Added resolute to VM-backed scenario:**
  - Scenario 10 "Support HTTPS-in-HTTPS proxies"
- **Left unchanged:**
  - Scenario 2 "Attach command when proxy is configured"
  - Scenario 4 "Attach command when authenticated proxy is configured"
  - Scenario 9 "Enable realtime kernel through proxy on a machine with no internet"
- **Test note:** run skipped in-session; tracker updated to match the final feature-file edits

#### `realtime_kernel.feature`

- **Status:** ⏭️ Evaluated; no resolute test updates applied
- **Decision:** do not update this feature's release matrix
- **Reason:** realtime-kernel is no longer managed through Ubuntu Pro in the current product direction
- **TODO:** define the best way to make this explicit in test coverage, potentially by introducing a dedicated tombstone/deprecation test that asserts expected non-managed behavior instead of keeping legacy enable-flow expansion

#### `reboot_cmds.feature`

- **Status:** ⏭️ Evaluated; not applicable to resolute
- **Decision:** no resolute additions
- **Reason:** this scenario is focal-only and validates FIPS-specific reboot command behavior with hardcoded package/version expectations (`strongswan` and `fips` flow). Resolute applicability is not established in the current FIPS support matrix.
- **Revisit:** re-evaluate if/when resolute gains the required FIPS reboot-cmd behavior and package expectations for this flow.

#### `retry_auto_attach.feature`

- **Status:** ✅ Updated
- **Scenarios 1-5** (auto-attach retry flow/status updates, manual recovery, gcp auto-detect retry path, and eventual-success cleanup): added `resolute` rows following existing noble cloud matrices
- **Machine types updated:** `azure.generic`, `gcp.generic`, `aws.generic`, `aws.pro`, `azure.pro`, `gcp.pro`
- **Reason:** scenario assertions are retry-state/status and message-flow checks, with no release-specific package/version coupling in the matrices
- **Test note:** run skipped in-session; this feature is cloud-only and requires cloud instance coverage

#### `ros.feature`

- **Status:** ⏭️ Evaluated; not applicable to resolute
- **Decision:** no resolute additions
- **Reason:** this feature is legacy-scoped with a xenial/bionic-only matrix and explicit ROS ESM source URL assertions tied to those releases.
- **Revisit:** re-evaluate only if ROS entitlement coverage is intentionally expanded to newer releases with updated source expectations.

#### `subscription_attach_restrictions.feature`

- **Status:** ✅ Updated
- **Scenario 1** "Attach fail if subscription is restricted to release": added `resolute | lxd-container | noble | 24.04 LTS | Noble Numbat`
- **Scenario 2** "Check notice visible when attached with onlySeries present": added `resolute | lxd-container | resolute | 26.04 LTS | Resolute Raccoon`
- **Scenario 3** "Check attach works with future onlyseries": added `resolute | lxd-container`
- **Reason:** scenarios validate attach restriction and messaging behavior using response overlays and release-parameterized expectations; no hardcoded package/version coupling blocks resolute coverage
- **Test note:** run skipped in-session per ongoing workflow

#### `timer.feature`

- **Status:** ✅ Partially updated
- **Scenario 1** "Timer is stopped when detached, started when attached": dropped `plucky`; added `resolute | lxd-container`
- **Scenario 2** "Run timer script on an attached machine": dropped `plucky`; added `resolute | lxd-container`
- **Scenario 3** "Run timer script to validate machine activity endpoint": added `resolute | lxd-container`
- **Reason:** timer/service behavior and contract activity validation are release-agnostic in these scenarios and follow existing noble/questing LTS progression
- **Test note:** run skipped in-session per ongoing workflow

#### `ubuntu_pro.feature`

- **Status:** ✅ Partially updated
- **Added resolute to:**
  - Scenario 2 "Attached refresh in an Ubuntu pro cloud machine" (`aws.pro`, `azure.pro`, `gcp.pro`)
  - Scenario 3 "Auto-attach service works on Pro Machine" (`azure.pro`, `gcp.pro`)
  - Scenario 4 "Auto-attach service works on Pro Machine on aws.pro" (`resolute`)
  - Scenario 5 "Auto-attach service works on Pro Machine on aws.generic" (`resolute | aws.generic`)
  - Scenario 6 "Auto-attach no-op when cloud-init has ubuntu_advantage on userdata" (`resolute` rows with `ubuntu_pro` key)
  - Scenario 7 "Unregistered Pro machine" (`resolute | aws.generic`)
- **Left unchanged:**
  - Scenario 1 "Proxy auto-attach on a cloud Ubuntu Pro machine" (legacy xenial/bionic/focal matrix retained)
- **Reason:** scenarios 2-7 are generic auto-attach/Pro-image behaviors already covered through noble; scenario 1 remains on its existing older matrix.
- **Test note:** run skipped in-session; cloud-instance coverage required

#### `ubuntu_pro_fips.feature`

- **Status:** ⏭️ Evaluated; not applicable to resolute
- **Decision:** no resolute additions
- **Reason:** the feature is a FIPS cloud-image matrix scoped to xenial/bionic/focal (`*.pro-fips` machine types) with release-specific kernel/meta/package expectations; resolute FIPS cloud coverage is not established in this file.
- **Revisit:** re-evaluate when resolute FIPS cloud image support and expected package/kernel behavior are confirmed.

#### `ubuntu_upgrade.feature`

- **Status:** ✅ Partially updated
- **Scenario 1** "Attached upgrade": added `questing | lxd-container | resolute | normal | (no --devel-release) | esm-infra n/a | esm-apps n/a | true`
- **Scenarios 2-4:** left unchanged (FIPS LTS-only upgrade path, onlySeries legacy chain, and `esm-infra-legacy` xenial->bionic coverage)
- **Reason:** scenario 1 tracks generic attached upgrade behavior across release hops; other scenarios are tightly scoped to legacy/FIPS-specific upgrade chains.
- **Test note:** run skipped in-session. Need AppArmor fix upstream.

#### `ubuntu_upgrade_unattached.feature`

- **Status:** ✅ Updated
- **Scenario 1** "Unattached upgrade": added `questing | lxd-container | resolute | normal | (no --devel-release) | n/a`
- **Reason:** extends the existing unattached release-hop chain to cover resolute, matching the attached-upgrade questing->resolute progression.
- **Test note:** run skipped in-session per ongoing workflow

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
