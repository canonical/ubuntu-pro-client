import mock
import pytest

from lib.migrate_user_config import (
    create_new_uaclient_conffile,
    create_new_user_config_file,
    load_pre_upgrade_conf,
)
from ubuntupro import messages
from ubuntupro.testing.fakes import FakeFile
from ubuntupro.yaml import safe_load


class TestLoadPreUpgradeConf:
    @pytest.mark.parametrize(
        ["contents"],
        [
            (
                """\
contracts_url: urlhere
log_level: debug
features: {allow_beta: true}
""",
            )
        ],
    )
    @mock.patch("builtins.open")
    def test_success(self, m_open, contents, capsys):
        m_open.return_value = FakeFile(contents)
        assert safe_load(contents) == load_pre_upgrade_conf()
        assert ("", "") == capsys.readouterr()

    @pytest.mark.parametrize(
        ["contents"],
        [
            (
                """\
contracts_url: {invalid
""",
            )
        ],
    )
    @mock.patch("builtins.open")
    def test_invalid_yaml(self, m_open, contents, capsys):
        m_open.return_value = FakeFile(contents)
        assert load_pre_upgrade_conf() is None
        assert (
            "",
            messages.USER_CONFIG_MIGRATION_WARNING_UACLIENT_CONF_LOAD + "\n",
        ) == capsys.readouterr()

    @mock.patch("builtins.open")
    def test_file_access_error(self, m_open, capsys):
        m_open.side_effect = Exception()
        assert load_pre_upgrade_conf() is None
        assert (
            "",
            messages.USER_CONFIG_MIGRATION_WARNING_UACLIENT_CONF_LOAD + "\n",
        ) == capsys.readouterr()


class TestCreateNewUserConfigFile:
    @pytest.mark.parametrize(
        ["old_conf", "expected_msg"],
        [
            ({}, ""),
            ({"log_level": "warning"}, ""),
            ({"ua_config": "invalid"}, ""),
            ({"ua_config": {"apt_news": True}}, ""),
            (
                {"ua_config": {"apt_news": False}},
                messages.USER_CONFIG_MIGRATION_WARNING_NEW_USER_CONFIG_WRITE
                + "\n           pro config set apt_news=False\n",
            ),
            (
                {"ua_config": {"apt_news": False, "http_proxy": "custom"}},
                messages.USER_CONFIG_MIGRATION_WARNING_NEW_USER_CONFIG_WRITE
                + "\n"
                + "           pro config set apt_news=False\n"
                + "           pro config set http_proxy=custom\n",
            ),
        ],
    )
    @mock.patch("builtins.open")
    def test_file_access_error(self, m_open, old_conf, expected_msg, capsys):
        m_open.side_effect = Exception()
        create_new_user_config_file(old_conf)
        assert ("", expected_msg) == capsys.readouterr()

    @pytest.mark.parametrize(
        ["old_conf", "new_user_config"],
        [
            ({}, {}),
            ({"log_level": "warning"}, {}),
            ({"ua_config": "invalid"}, {}),
            ({"ua_config": {"apt_news": True}}, {}),
            ({"ua_config": {"apt_news": False}}, {"apt_news": False}),
            (
                {"ua_config": {"apt_news": False, "http_proxy": "custom"}},
                {"http_proxy": "custom", "apt_news": False},
            ),
        ],
    )
    @mock.patch("json.dump")
    @mock.patch("builtins.open")
    def test_success(
        self, m_open, m_json_dump, old_conf, new_user_config, capsys
    ):
        create_new_user_config_file(old_conf)
        assert [
            mock.call(new_user_config, mock.ANY)
        ] == m_json_dump.call_args_list
        assert ("", "") == capsys.readouterr()


class TestCreateNewUaclientConffile:
    @pytest.mark.parametrize(
        ["old_conf", "expected_msg"],
        [
            (
                {},
                messages.USER_CONFIG_MIGRATION_MIGRATING
                + "\n"
                + messages.USER_CONFIG_MIGRATION_WARNING_NEW_UACLIENT_CONF_WRITE  # noqa: E501
                + "\n"
                + "           contract_url: 'https://contracts.canonical.com'\n"  # noqa: E501
                + "           log_level: 'debug'\n",
            ),
            (
                {"log_level": "debug"},
                messages.USER_CONFIG_MIGRATION_MIGRATING
                + "\n"
                + messages.USER_CONFIG_MIGRATION_WARNING_NEW_UACLIENT_CONF_WRITE  # noqa: E501
                + "\n"
                + "           contract_url: 'https://contracts.canonical.com'\n"  # noqa: E501
                + "           log_level: 'debug'\n",
            ),
            (
                {"log_level": "warning"},
                messages.USER_CONFIG_MIGRATION_MIGRATING
                + "\n"
                + messages.USER_CONFIG_MIGRATION_WARNING_NEW_UACLIENT_CONF_WRITE  # noqa: E501
                + "\n"
                + "           contract_url: 'https://contracts.canonical.com'\n"  # noqa: E501
                + "           log_level: 'warning'\n",
            ),
            (
                {"features": {}},
                messages.USER_CONFIG_MIGRATION_MIGRATING
                + "\n"
                + messages.USER_CONFIG_MIGRATION_WARNING_NEW_UACLIENT_CONF_WRITE  # noqa: E501
                + "\n"
                + "           contract_url: 'https://contracts.canonical.com'\n"  # noqa: E501
                + "           features: {}\n"
                + "           log_level: 'debug'\n",
            ),
        ],
    )
    @mock.patch("os.rename")
    @mock.patch("builtins.open")
    def test_file_access_error(
        self, m_open, _m_rename, old_conf, expected_msg, capsys
    ):
        m_open.side_effect = Exception()
        create_new_uaclient_conffile(old_conf)
        assert ("", expected_msg) == capsys.readouterr()

    @pytest.mark.parametrize(
        ["old_conf", "new_uaclient_conf"],
        [
            (
                {},
                {
                    "contract_url": "https://contracts.canonical.com",
                    "log_level": "debug",
                },
            ),
            (
                {"log_level": "warning"},
                {
                    "contract_url": "https://contracts.canonical.com",
                    "log_level": "warning",
                },
            ),
            (
                {"features": {"allow_beta": True}},
                {
                    "contract_url": "https://contracts.canonical.com",
                    "log_level": "debug",
                    "features": {"allow_beta": True},
                },
            ),
            (
                {
                    "contract_url": "https://contracts.canonical.com",
                    "log_level": "debug",
                    "log_file": "/var/log/ubuntu-advantage.log",
                    "daemon_log_file": "/var/log/ubuntu-advantage-daemon.log",
                    "timer_log_file": "/var/log/ubuntu-advantage-timer.log",
                    "data_dir": "/var/lib/ubuntu-advantage",
                    "ua_config": {"apt_news": False},
                },
                {
                    "contract_url": "https://contracts.canonical.com",
                    "log_level": "debug",
                },
            ),
            (
                {
                    "contract_url": "https://contracts.canonical.com",
                    "log_level": "debug",
                    "log_file": "/var/log/ubuntu-advantage.log",
                    "data_dir": "/var/lib/custom",
                },
                {
                    "contract_url": "https://contracts.canonical.com",
                    "log_level": "debug",
                    "data_dir": "/var/lib/custom",
                },
            ),
        ],
    )
    @mock.patch("os.rename")
    @mock.patch("lib.migrate_user_config.safe_dump")
    @mock.patch("builtins.open")
    def test_success(
        self,
        m_open,
        m_yaml_dump,
        _m_rename,
        old_conf,
        new_uaclient_conf,
        capsys,
    ):
        create_new_uaclient_conffile(old_conf)
        assert [
            mock.call(new_uaclient_conf, default_flow_style=False)
        ] == m_yaml_dump.call_args_list
        assert (
            "",
            messages.USER_CONFIG_MIGRATION_MIGRATING + "\n",
        ) == capsys.readouterr()
