import os

from configparser import ConfigParser


PIP_CONFIG_FILE = "/etc/pip.conf"


def _write_pip_conf(pip_conf):
    """
    Write a pip ConfigParser object into
    a predefined path.

    :param pip_conf:
        A ConfigParser object representing a pip config file
    """
    with open(PIP_CONFIG_FILE, "w") as f:
        pip_conf.write(f)


def _load_pip_conf():
    """
    Parser and returns a pip.conf file in a predefined path

    :return:
        A ConfigParser object representing the pip config file
    """
    conf_parser = ConfigParser()
    with open(PIP_CONFIG_FILE, "r") as pip_conf:
        conf_parser.read_file(pip_conf)

    return conf_parser


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
        existing_conf_parser = _load_pip_conf()
        existing_conf_parser.update(new_conf_parser)
        new_conf_parser = existing_conf_parser

    _write_pip_conf(new_conf_parser)
