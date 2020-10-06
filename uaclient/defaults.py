"""
Project-wide default settings

These are in their own file so they can be imported by setup.py before we have
any of our dependencies installed.
"""

UAC_ETC_PATH = "/etc/ubuntu-advantage/"
DEFAULT_CONFIG_FILE = UAC_ETC_PATH + "uaclient.conf"
DEFAULT_HELP_FILE = UAC_ETC_PATH + "help_data.yaml"
DEFAULT_UPGRADE_CONTRACT_FLAG_FILE = UAC_ETC_PATH + "request-update-contract"
BASE_CONTRACT_URL = "https://contracts.canonical.com"

CONFIG_DEFAULTS = {
    "contract_url": BASE_CONTRACT_URL,
    "data_dir": "/var/lib/ubuntu-advantage",
    "log_level": "INFO",
    "log_file": "/var/log/ubuntu-advantage.log",
}
