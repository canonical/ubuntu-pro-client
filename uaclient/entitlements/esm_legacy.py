from uaclient import messages
from uaclient.entitlements import repo


class ESMInfraLegacyEntitlement(repo.RepoEntitlement):
    name = "esm-infra-legacy"
    origin = "UbuntuESM"
    title = messages.ESM_INFRA_LEGACY_TITLE
    description = messages.ESM_INFRA_LEGACY_DESCRIPTION
    help_text = messages.ESM_INFRA_LEGACY_HELP_TEXT
    repo_key_file = "ubuntu-pro-esm-infra-legacy.gpg"


class ESMAppsLegacyEntitlement(repo.RepoEntitlement):
    name = "esm-apps-legacy"
    origin = "UbuntuESMApps"
    title = messages.ESM_APPS_LEGACY_TITLE
    description = messages.ESM_APPS_LEGACY_DESCRIPTION
    help_text = messages.ESM_APPS_LEGACY_HELP_TEXT
    repo_key_file = "ubuntu-pro-esm-apps-legacy.gpg"
