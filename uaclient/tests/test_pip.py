"""Tests related to uaclient.pip module."""

import mock
import pytest

from textwrap import dedent

from uaclient.pip import update_pip_conf


class TestPipConfUpdate:
    def test_config_dict(self):
        """
        Create a base config dict to be used on tests. This
        config is based on the possible config that will
        be used by the esm-apps-python service.
        """
        index_url = "http://bearer:token@python.esm.ubuntu.com/simple"
        index = index_url

        return {"global": {"index-url": index_url, "index": index}}

    @pytest.mark.parametrize(
        "file_content,expected",
        (
            (
                "",
                dedent(
                    """\
                [global]
                index-url = http://bearer:token@python.esm.ubuntu.com/simple
                index = http://bearer:token@python.esm.ubuntu.com/simple
                """
                ),
            ),
            (
                dedent(
                    """\
                [freeze]
                timeout = 10
                """
                ),
                dedent(
                    """\
                [freeze]
                timeout = 10

                [global]
                index-url = http://bearer:token@python.esm.ubuntu.com/simple
                index = http://bearer:token@python.esm.ubuntu.com/simple
                """
                ),
            ),
            (
                dedent(
                    """\
                [global]
                index-url = www.mypip.com
                """
                ),
                dedent(
                    """\
                [global]
                index-url = http://bearer:token@python.esm.ubuntu.com/simple
                index = http://bearer:token@python.esm.ubuntu.com/simple
                """
                ),
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
                dedent(
                    """\
                [global]
                index-url = http://bearer:token@python.esm.ubuntu.com/simple
                index = http://bearer:token@python.esm.ubuntu.com/simple

                [freeze]
                timeout = 10
                """
                ),
            ),
            (
                None,
                dedent(
                    """\
                [global]
                index-url = http://bearer:token@python.esm.ubuntu.com/simple
                index = http://bearer:token@python.esm.ubuntu.com/simple
                """
                ),
            ),
        ),
    )
    def test_update_pip_conf(self, tmpdir, file_content, expected):
        file_path = tmpdir / "pip.conf"

        if file_content:
            with file_path.open("w") as f:
                f.write(file_content)

        with mock.patch("uaclient.pip.PIP_CONFIG_FILE", file_path.strpath):
            update_pip_conf(self.test_config_dict())

        with file_path.open("r") as f:
            assert f.read().strip() == expected.strip()
