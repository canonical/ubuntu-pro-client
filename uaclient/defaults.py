"""
Project-wide default settings

These are in their own file so they can be imported by setup.py before we have
any of our dependencies installed.
"""

import os

# Base directories
UAC_ETC_PATH = "/etc/ubuntu-advantage"
UAC_RUN_PATH = "/run/ubuntu-advantage"
DEFAULT_DATA_DIR = "/var/lib/ubuntu-advantage"
DEFAULT_LOG_DIR = "/var/log"


# Relative paths
MACHINE_TOKEN_FILE = "machine-token.json"
CONFIG_FILE = "uaclient.conf"
USER_CONFIG_FILE = "user-config.json"
CANDIDATE_VERSION_FILE = "candidate-version"
DEFAULT_LOG_FILE_BASE_NAME = "ubuntu-advantage"
PRIVATE_SUBDIR = "private"
MESSAGES_SUBDIR = "messages"
USER_CACHE_SUBDIR = "ubuntu-pro"
NOTICES_SUBDIR = "notices"
PRIVATE_ESM_CACHE_SUBDIR = "apt-esm"

DEFAULT_PRIVATE_MACHINE_TOKEN_PATH = os.path.join(
    DEFAULT_DATA_DIR, PRIVATE_SUBDIR, MACHINE_TOKEN_FILE
)
DEFAULT_PRIVATE_DATA_DIR = os.path.join(DEFAULT_DATA_DIR, PRIVATE_SUBDIR)
MESSAGES_DIR = os.path.join(DEFAULT_DATA_DIR, MESSAGES_SUBDIR)
DEFAULT_CONFIG_FILE = os.path.join(UAC_ETC_PATH, CONFIG_FILE)
CANDIDATE_CACHE_PATH = os.path.join(UAC_RUN_PATH, CANDIDATE_VERSION_FILE)
DEFAULT_USER_CONFIG_JSON_FILE = os.path.join(
    DEFAULT_DATA_DIR, USER_CONFIG_FILE
)
DEFAULT_LOG_PREFIX = os.path.join(DEFAULT_LOG_DIR, DEFAULT_LOG_FILE_BASE_NAME)
ESM_APT_ROOTDIR = os.path.join(DEFAULT_DATA_DIR, PRIVATE_ESM_CACHE_SUBDIR)
NOTICES_PERMANENT_DIRECTORY = os.path.join(DEFAULT_DATA_DIR, NOTICES_SUBDIR)
NOTICES_TEMPORARY_DIRECTORY = os.path.join(UAC_RUN_PATH, NOTICES_SUBDIR)


# URLs
BASE_CONTRACT_URL = "https://contracts.canonical.com"
BASE_SECURITY_URL = "https://ubuntu.com/security"
BASE_LIVEPATCH_URL = "https://livepatch.canonical.com"
APT_NEWS_URL = "https://motd.ubuntu.com/aptnews.json"

PRINT_WRAP_WIDTH = 80
CONTRACT_EXPIRY_GRACE_PERIOD_DAYS = 14
CONTRACT_EXPIRY_PENDING_DAYS = 20
ATTACH_FAIL_DATE_FORMAT = "%B %d, %Y"

DEFAULT_LOG_FORMAT = (
    "%(asctime)s - %(filename)s:(%(lineno)d) [%(levelname)s]: %(message)s"
)

CONFIG_DEFAULTS = {
    "contract_url": BASE_CONTRACT_URL,
    "security_url": BASE_SECURITY_URL,
    "data_dir": DEFAULT_DATA_DIR,
    "log_level": "debug",
    "log_file": "{}.log".format(DEFAULT_LOG_PREFIX),
}

CONFIG_FIELD_ENVVAR_ALLOWLIST = [
    "ua_data_dir",
    "ua_log_file",
    "ua_log_level",
    "ua_security_url",
]

ROOT_READABLE_MODE = 0o600
WORLD_READABLE_MODE = 0o644

CLOUD_BUILD_INFO = "/etc/cloud/build.info"
SSL_CERTS_PATH = "/etc/ssl/certs/ca-certificates.crt"

# used by apport, collect-logs, and tests
APPARMOR_PROFILES = [
    "/etc/apparmor.d/ubuntu_pro_apt_news",
    "/etc/apparmor.d/ubuntu_pro_esm_cache",
]
