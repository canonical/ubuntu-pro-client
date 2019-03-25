import json
import os

from nose2.tools.params import params

from uaclient.config import UAConfig
from uaclient.testing.helpers import TestCase


# These are in a variable rather than inline to work around
# https://github.com/nose-devs/nose2/issues/433
SIMPLE_PARAMS = (('machine_token', 'machine-token', None),
                 ('contracts', 'account-contracts', []))

KNOWN_DATA_PATHS = (('bound-macaroon', 'bound-macaroon'),
                    ('accounts', 'accounts.json'))


class TestDataPath(TestCase):

    def test_data_path_returns_data_dir_path_without_key(self):
        """The data_path method returns the data_dir when key is absent."""
        cfg = UAConfig({'data_dir': '/my/dir'})
        assert '/my/dir' == cfg.data_path()

    @params(*KNOWN_DATA_PATHS)
    def test_data_path_returns_file_path_with_defined_data_paths(
            self, key, path_basename):
        """When key is defined in Config.data_paths return data_path value."""
        cfg = UAConfig({'data_dir': '/my/dir'})
        assert '/my/dir/%s' % path_basename == cfg.data_path(key=key)

    @params(('notHere', 'notHere'), ('anything', 'anything'))
    def test_data_path_returns_file_path_with_undefined_data_paths(
            self, key, path_basename):
        """When key is not in Config.data_paths the key is used to data_dir"""
        cfg = UAConfig({'data_dir': '/my/dir'})
        assert '/my/dir/%s' % key == cfg.data_path(key=key)


class TestReadCache(TestCase):

    @params(*KNOWN_DATA_PATHS)
    def test_read_cache_returns_none_when_data_path_absent(
            self, key, path_basename):
        """The data_path method returns the data_dir when key is absent."""
        cfg = UAConfig({'data_dir': '/my/dir'})
        assert None is cfg.read_cache(key)
        assert False is os.path.exists(os.path.join('/my/dir', path_basename))

    @params(*KNOWN_DATA_PATHS)
    def test_read_cache_returns_content_when_data_path_present(
            self, key, path_basename):
        tmp_dir = self.tmp_dir()
        cfg = UAConfig({'data_dir': tmp_dir})
        data_path = self.tmp_path(path_basename, tmp_dir)
        with open(data_path, 'w') as f:
            f.write('content%s' % key)

        assert 'content%s' % key == cfg.read_cache(key)

    @params(*KNOWN_DATA_PATHS)
    def test_read_cache_returns_stuctured_content_when_json_data_path_present(
            self, key, path_basename):
        tmp_dir = self.tmp_dir()
        cfg = UAConfig({'data_dir': tmp_dir})
        data_path = self.tmp_path(path_basename, tmp_dir)
        expected = {key: 'content%s' % key}
        with open(data_path, 'w') as f:
            f.write(json.dumps(expected))

        assert expected == cfg.read_cache(key)
