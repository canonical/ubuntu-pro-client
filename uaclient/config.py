import copy
import logging
import os
import six
import yaml

LOG = logging.getLogger(__name__)

UA_VERSION = '18.1.0-{gitrev}'

DEFAULT_CONFIG_FILE = '/etc/uaclient/uaclient.conf'

CONFIG_DEFAULTS = {
    'service_url': 'https://uaservice.canonical.com:8080',
    'data_dir': '/var/lib/uaclient/',
    'log_level': 'info'
}


class ConfigAbsentError(RuntimeError):
    """Raised when no valid config is discovered."""
    pass


def decode_binary(blob, encoding='utf-8'):
    # Converts a binary type into a text type using given encoding.
    if isinstance(blob, six.string_types):
        return blob
    return blob.decode(encoding)


def load_file(fname, read_cb=None, decode=True):
    LOG.debug("Reading from '%s'", fname)
    try:
        with open(fname, 'rb') as ifh:
            content = ifh.read()
    except IOError as e:
        if not quiet:
            raise
        if e.errno != ENOENT:
            raise
    LOG.debug("Read %s bytes from %s", len(content), fname)
    if decode:
        return decode_binary(content)
    else:
        return content


def parse_config(config_path=None):
    """Parse known UA config file

    Attempt to find configuration in cwd and fallback to DEFAULT_CONFIG_FILE.
    Any missing configuration keys will be set to CONFIG_DEFAULTS.

    @param config_path: Fullpath to ua configfile. If unspecified, use
        DEFAULT_CONFIG_FILE.

    @raises: ConfigAbsentError when no config file is discovered.
    @return: Dict of configuration values.
    """
    if not config_path:
        config_path = DEFAULT_CONFIG_FILE
    cfg = copy.copy(CONFIG_DEFAULTS)
    local_cfg = os.path.join(os.getcwd(), os.path.basename(config_path))
    if os.path.exists(local_cfg):
        LOG.debug('Using local UA client configuration file at %s', local_cfg)
        config_path = local_cfg
    if not os.path.exists(config_path):
        msg = 'No UA client configuration file found at %s' % config_path
        LOG.error(msg)
        raise ConfigAbsentError(msg)
    cfg.update(yaml.load(load_file(config_path)))
    cfg['log_level'] = cfg['log_level'].upper()
    return cfg


def print_version(_args=None):
    print(get_version())

def get_version(_args=None):
    if 'gitrev' not in UA_VERSION:
        return UA_VERSION
    return UA_VERSION.format(gitrev='dev')
