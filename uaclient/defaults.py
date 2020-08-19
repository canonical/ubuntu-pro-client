"""
Project-wide default settings

These are in their own file so they can be imported by setup.py before we have
any of our dependencies installed.
"""

DEFAULT_CONFIG_FILE = "/etc/ubuntu-advantage/uaclient.conf"
DEFAULT_HELP_FILE = "/etc/ubuntu-advantage/help_data.yaml"
BASE_CONTRACT_URL = "https://contracts.canonical.com"

CONFIG_DEFAULTS = {
    "contract_url": BASE_CONTRACT_URL,
    "data_dir": "/var/lib/ubuntu-advantage",
    "log_level": "INFO",
    "log_file": "/var/log/ubuntu-advantage.log",
}

DEFAULT_HELP = {
    "esm-infra": {"help": "esm-infra help\nInformation about esm-infra"}
}
