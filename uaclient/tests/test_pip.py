"""Tests related to uaclient.pip module."""

import mock
import pytest

from textwrap import dedent
from configparser import ConfigParser

from uaclient.pip import update_pip_conf


class TestPipConfUpdate:
    index_url = "http://bearer:token@python.esm.ubuntu.com/simple"

    def _get_config_dict(self):
        """
        Create a base config dict to be used on tests. This
        config is based on the possible config that will
        be used by the esm-apps-python service.
        """
        index_url = self.index_url
        index = index_url

        return {"global": {"index-url": index_url, "index": index}}

    def _cfg_to_dict(self, cfg_file):
        """Return a ConfigParser dict representation of a config file."""
        cfg_parser = ConfigParser()
        cfg_parser.read(cfg_file)
        cfg_dict = {}
        for s in cfg_parser.sections():
            cfg_dict[s] = {}

            for option in cfg_parser[s]:
                cfg_dict[s][option] = cfg_parser[s][option]

        return cfg_dict

    @pytest.mark.parametrize(
        "file_content,expected",
        (
            ("", {"global": {"index-url": index_url, "index": index_url}}),
            (
                dedent(
                    """\
                [freeze]
                timeout = 10
                """
                ),
                {
                    "global": {"index-url": index_url, "index": index_url},
                    "freeze": {"timeout": "10"},
                },
            ),
            (
                dedent(
                    """\
                [global]
                index-url = www.mypip.com
                """
                ),
                {"global": {"index-url": index_url, "index": index_url}},
            ),
            (
                dedent(
                    """\
                [global]
                index-url = www.mypip.com

                [freeze]
                timeout = 10
                """
                ),
                {
                    "global": {"index-url": index_url, "index": index_url},
                    "freeze": {"timeout": "10"},
                },
            ),
            (None, {"global": {"index-url": index_url, "index": index_url}}),
        ),
    )
    def test_update_pip_conf(self, tmpdir, file_content, expected):
        file_path = tmpdir / "pip.conf"

        if file_content:
            file_path.write(file_content)

        with mock.patch("uaclient.pip.PIP_CONFIG_FILE", file_path.strpath):
            update_pip_conf(self._get_config_dict())

        assert self._cfg_to_dict(file_path.strpath) == expected
