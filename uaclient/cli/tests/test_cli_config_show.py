import mock
import pytest

from uaclient.cli import main
from uaclient.cli.config import show_subcommand

M_PATH = "uaclient.cli."


@mock.patch("uaclient.cli.logging.error")
@mock.patch("uaclient.log.setup_cli_logging")
@mock.patch("uaclient.contract.get_available_resources")
class TestMainConfigShow:
    def test_config_show_error_on_invalid_subcommand(
        self, _m_resources, _logging, _logging_error, capsys, FakeConfig
    ):
        """Exit 1 on invalid subcommands."""
        with pytest.raises(SystemExit):
            with mock.patch("sys.argv", ["/usr/bin/ua", "config", "invalid"]):
                with mock.patch(
                    "uaclient.config.UAConfig",
                    return_value=FakeConfig(),
                ):
                    main()
        out, err = capsys.readouterr()
        assert "" == out
        expected_logs = [
            "usage: pro config [-h] {show,set,unset} ...",
            "argument command: invalid choice: 'invalid' (choose from 'show',"
            " 'set', 'unset')",
        ]
        for log in expected_logs:
            assert log in err


class TestActionConfigShow:
    @pytest.mark.parametrize(
        "optional_key",
        (
            None,
            "https_proxy",
            "http_proxy",
            "global_apt_http_proxy",
            "global_apt_https_proxy",
        ),
    )
    def test_show_values_and_limit_when_optional_key_provided(
        self, optional_key, FakeConfig, capsys
    ):
        cfg = FakeConfig()
        cfg.user_config.http_proxy = "http://http_proxy"
        cfg.user_config.https_proxy = "http://https_proxy"
        cfg.user_config.global_apt_http_proxy = "http://global_apt_http_proxy"
        cfg.user_config.global_apt_https_proxy = (
            "http://global_apt_https_proxy"
        )
        args = mock.MagicMock(key=optional_key)
        show_subcommand.action(args, cfg=cfg)
        out, err = capsys.readouterr()
        if optional_key:
            assert "{key} http://{key}\n".format(key=optional_key) == out
        else:
            assert (
                """\
http_proxy              http://http_proxy
https_proxy             http://https_proxy
apt_http_proxy          None
apt_https_proxy         None
ua_apt_http_proxy       None
ua_apt_https_proxy      None
global_apt_http_proxy   http://global_apt_http_proxy
global_apt_https_proxy  http://global_apt_https_proxy
update_messaging_timer  21600
metering_timer          14400
apt_news                True
apt_news_url            https://motd.ubuntu.com/aptnews.json
"""
                == out
            )
        assert "" == err
