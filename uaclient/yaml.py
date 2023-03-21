import logging
import sys

from uaclient.messages import BROKEN_YAML_MODULE, MISSING_YAML_MODULE

try:
    import yaml
except ImportError:
    logging.error(MISSING_YAML_MODULE.msg)
    sys.exit(1)


def safe_load(stream):
    try:
        return yaml.safe_load(stream)
    except AttributeError:
        logging.error(BROKEN_YAML_MODULE.format(path=yaml.__path__).msg)
        sys.exit(1)


def safe_dump(data, stream=None, **kwargs):
    try:
        return yaml.safe_dump(data, stream, **kwargs)
    except AttributeError:
        logging.error(BROKEN_YAML_MODULE.format(path=yaml.__path__).msg)
        sys.exit(1)


parser = yaml.parser
