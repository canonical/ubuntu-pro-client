"""
Project-wide default settings

These are in their own file so they can be imported by setup.py before we have
any of our dependencies installed.
"""

DEFAULT_CONFIG_FILE = '/etc/ubuntu-advantage/uaclient.conf'
BASE_AUTH_URL = 'https://login.ubuntu.com'
BASE_SERVICE_URL = 'https://uaservice.canonical.com'

CONFIG_DEFAULTS = {
    'sso_auth_url': BASE_AUTH_URL,
    'service_url': BASE_SERVICE_URL,
    'data_dir': '/var/lib/ubuntu-advantage',
    'log_level': 'INFO',
    'log_file': '/var/log/ubuntu-advantage.log'
}
