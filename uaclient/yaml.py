import logging
import sys

from uaclient import util
from uaclient.messages import BROKEN_YAML_MODULE, MISSING_YAML_MODULE

LOG = logging.getLogger(util.replace_top_level_logger_name(__name__))

try:
    import yaml
except ImportError as e:
    LOG.exception(e)
    print(MISSING_YAML_MODULE, file=sys.stderr)
    sys.exit(1)


def safe_load(stream):
    try:
        return yaml.safe_load(stream)
    except AttributeError as e:
        LOG.exception(e)
        print(BROKEN_YAML_MODULE.format(path=yaml.__path__), file=sys.stderr)
        sys.exit(1)


def safe_dump(data, stream=None, **kwargs):
    try:
        return yaml.safe_dump(data, stream, **kwargs)
    except AttributeError as e:
        LOG.exception(e)
        print(BROKEN_YAML_MODULE.format(path=yaml.__path__), file=sys.stderr)
        sys.exit(1)


parser = yaml.parser
