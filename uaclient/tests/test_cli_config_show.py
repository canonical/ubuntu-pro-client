import mock
import pytest

from uaclient.cli import action_config_show, main

M_PATH = "uaclient.cli."

HELP_OUTPUT = """\
usage: ua config <command> [flags]

Manage Ubuntu Advantage configuration

Flags:
  -h, --help  show this help message and exit

Available Commands:
  
    show      show all Ubuntu Advantage configuration setting(s)
    set       set Ubuntu Advantage configuration setting
    unset     unset Ubuntu Advantage configuration setting
"""  # noqa


@mock.patch("uaclient.cli.logging.error")
@mock.patch("uaclient.cli.setup_logging")
class TestMainConfigShow:
    @pytest.mark.parametrize("additional_params", ([], ["--help"]))
    def test_config_show_help(
        self, _logging, logging_error, additional_params, capsys
    ):
        """Show help for --help and absent positional param"""
        with pytest.raises(SystemExit):
            with mock.patch(
                "sys.argv", ["/usr/bin/ua", "config"] + additional_params
            ):
                main()
        out, err = capsys.readouterr()
        assert HELP_OUTPUT == out
        if additional_params == ["--help"]:
            assert "" == err
        else:
            # When lacking show, set or unset inform about valid values
            assert "\n<command> must be one of: show, set, unset\n" == err
            assert [
                mock.call("\n<command> must be one of: show, set, unset")
            ] == logging_error.call_args_list

    def test_config_show_error_on_invalid_subcommand(
        self, _logging, _logging_error, capsys
    ):
        """Exit 1 on invalid subcommands."""
        with pytest.raises(SystemExit):
            with mock.patch("sys.argv", ["/usr/bin/ua", "config", "invalid"]):
                main()
        out, err = capsys.readouterr()
        assert "" == out
        expected_logs = [
            "usage: ua config <command> [flags]",
            "argument : invalid choice: 'invalid' (choose from 'show', 'set',"
            " 'unset')",
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
            "apt_http_proxy",
            "apt_https_proxy",
        ),
    )
    @mock.patch("uaclient.config.UAConfig.write_cfg")
    def test_show_values_and_limit_when_optional_key_provided(
        self, _write_cfg, optional_key, FakeConfig, capsys
    ):
        cfg = FakeConfig()
        cfg.http_proxy = "http://http_proxy"
        cfg.https_proxy = "http://https_proxy"
        cfg.apt_http_proxy = "http://apt_http_proxy"
        cfg.apt_https_proxy = "http://apt_https_proxy"
        args = mock.MagicMock(key=optional_key)
        action_config_show(args, cfg=cfg)
        out, err = capsys.readouterr()
        if optional_key:
            assert "{key} http://{key}\n".format(key=optional_key) == out
        else:
            assert (
                """\
http_proxy              http://http_proxy
https_proxy             http://https_proxy
apt_http_proxy          http://apt_http_proxy
apt_https_proxy         http://apt_https_proxy
update_messaging_timer  None
update_status_timer     None
gcp_auto_attach_timer   None
"""
                == out
            )
        assert "" == err
