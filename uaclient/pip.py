import os
from configparser import ConfigParser

PIP_CONFIG_FILE = "/etc/pip.conf"


def update_pip_conf(pip_config_dict):
    """
    Update pip.conf file on /etc/ with the required configurations
    for enabling a service.

    :param pip_config_dict:
        A dictionaty representing a valid pip config
    """
    new_conf_parser = ConfigParser()
    new_conf_parser.read_dict(pip_config_dict)

    if os.path.exists(PIP_CONFIG_FILE):
        existing_conf_parser = ConfigParser()
        with open(PIP_CONFIG_FILE, "r") as f:
            existing_conf_parser.read_file(f)

        existing_conf_parser.update(new_conf_parser)
        new_conf_parser = existing_conf_parser

    with open(PIP_CONFIG_FILE, "w") as f:
        new_conf_parser.write(f)
