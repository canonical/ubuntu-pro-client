"""
Project-wide default settings

These are in their own file so they can be imported by setup.py before we have
any of our dependencies installed.
"""

UAC_ETC_PATH = "/etc/ubuntu-advantage/"
UAC_RUN_PATH = "/run/ubuntu-advantage/"
DEFAULT_DATA_DIR = "/var/lib/ubuntu-advantage"
MACHINE_TOKEN_FILE = "machine-token.json"
PRIVATE_SUBDIR = "private"
DEFAULT_PRIVATE_MACHINE_TOKEN_PATH = (
    DEFAULT_DATA_DIR + "/" + PRIVATE_SUBDIR + "/" + MACHINE_TOKEN_FILE
)
DEFAULT_PRIVATE_DATA_DIR = DEFAULT_DATA_DIR + "/" + PRIVATE_SUBDIR
MESSAGES_SUBDIR = "/messages"
MESSAGES_DIR = DEFAULT_DATA_DIR + MESSAGES_SUBDIR
CANDIDATE_CACHE_PATH = UAC_RUN_PATH + "candidate-version"
DEFAULT_CONFIG_FILE = UAC_ETC_PATH + "uaclient.conf"
DEFAULT_USER_CONFIG_JSON_FILE = DEFAULT_DATA_DIR + "/user-config.json"
DEFAULT_UPGRADE_CONTRACT_FLAG_FILE = UAC_ETC_PATH + "request-update-contract"
BASE_CONTRACT_URL = "https://contracts.canonical.com"
BASE_SECURITY_URL = "https://ubuntu.com/security"
BASE_LIVEPATCH_URL = "https://livepatch.canonical.com"
APT_NEWS_URL = "https://motd.ubuntu.com/aptnews.json"
CLOUD_BUILD_INFO = "/etc/cloud/build.info"
ESM_APT_ROOTDIR = DEFAULT_DATA_DIR + "/apt-esm/"

PRINT_WRAP_WIDTH = 80
CONTRACT_EXPIRY_GRACE_PERIOD_DAYS = 14
CONTRACT_EXPIRY_PENDING_DAYS = 20
ATTACH_FAIL_DATE_FORMAT = "%B %d, %Y"
DEFAULT_LOG_DIR = "/var/log"
DEFAULT_LOG_FILE_BASE_NAME = "ubuntu-advantage"
DEFAULT_LOG_PREFIX = DEFAULT_LOG_DIR + "/" + DEFAULT_LOG_FILE_BASE_NAME
DEFAULT_LOG_FORMAT = (
    "%(asctime)s - %(filename)s:(%(lineno)d) [%(levelname)s]: %(message)s"
)

CONFIG_DEFAULTS = {
    "contract_url": BASE_CONTRACT_URL,
    "security_url": BASE_SECURITY_URL,
    "data_dir": DEFAULT_DATA_DIR,
    "log_level": "debug",
    "log_file": "/var/log/ubuntu-advantage.log",
}

CONFIG_FIELD_ENVVAR_ALLOWLIST = [
    "ua_data_dir",
    "ua_log_file",
    "ua_log_level",
    "ua_security_url",
]

ROOT_READABLE_MODE = 0o600
WORLD_READABLE_MODE = 0o644
NOTICES_PERMANENT_DIRECTORY = DEFAULT_DATA_DIR + "/notices/"
NOTICES_TEMPORARY_DIRECTORY = UAC_RUN_PATH + "notices/"
USER_CACHE_SUBDIR = "ubuntu-pro"

SSL_CERTS_PATH = "/etc/ssl/certs/ca-certificates.crt"

# used by apport, collect-logs, and tests
APPARMOR_PROFILES = [
    "/etc/apparmor.d/ubuntu_pro_apt_news",
]
