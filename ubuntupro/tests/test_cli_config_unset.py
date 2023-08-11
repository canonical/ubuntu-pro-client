import mock
import pytest

from ubuntupro.cli import action_config_unset, main
from ubuntupro.entitlements.entitlement_status import ApplicationStatus
from ubuntupro.exceptions import NonRootUserError

HELP_OUTPUT = """\
usage: pro config unset <key> [flags]

Unset Ubuntu Pro configuration setting

positional arguments:
  key         configuration key to unset from Ubuntu Pro services. One of:
              http_proxy, https_proxy, apt_http_proxy, apt_https_proxy,
              ua_apt_http_proxy, ua_apt_https_proxy, global_apt_http_proxy,
              global_apt_https_proxy, update_messaging_timer, metering_timer,
              apt_news, apt_news_url

Flags:
  -h, --help  show this help message and exit
"""

M_LIVEPATCH = "ubuntupro.entitlements.livepatch."


@mock.patch("ubuntupro.cli.setup_logging")
@mock.patch("ubuntupro.cli.contract.get_available_resources")
class TestMainConfigUnSet:
    @pytest.mark.parametrize(
        "kv_pair,err_msg",
        (
            (
                "junk",
                "<key> must be one of: http_proxy, https_proxy,"
                " apt_http_proxy, apt_https_proxy, ua_apt_http_proxy,"
                " ua_apt_https_proxy, global_apt_http_proxy,"
                " global_apt_https_proxy, update_messaging_timer,"
                " metering_timer",
            ),
            (
                "http_proxys",
                "<key> must be one of: http_proxy, https_proxy,"
                " apt_http_proxy, apt_https_proxy, ua_apt_http_proxy,"
                " ua_apt_https_proxy, global_apt_http_proxy,"
                " global_apt_https_proxy, update_messaging_timer,"
                " metering_timer",
            ),
        ),
    )
    def test_set_error_with_help_on_invalid_key_value_pair(
        self,
        _m_resources,
        _logging,
        kv_pair,
        err_msg,
        capsys,
        FakeConfig,
    ):
        """Exit 1 and print help on invalid key_value_pair input param."""
        with pytest.raises(SystemExit):
            with mock.patch(
                "sys.argv", ["/usr/bin/ua", "config", "unset", kv_pair]
            ):
                with mock.patch(
                    "ubuntupro.config.UAConfig",
                    return_value=FakeConfig(),
                ):
                    main()
        out, err = capsys.readouterr()
        assert HELP_OUTPUT == out
        assert err_msg in err


@mock.patch("ubuntupro.config.state_files.user_config_file.write")
class TestActionConfigUnSet:
    @mock.patch("ubuntupro.util.we_are_currently_root", return_value=False)
    def test_set_error_on_non_root_user(
        self, we_are_currently_root, _write, FakeConfig
    ):
        """Root is required to run pro config unset."""
        args = mock.MagicMock(key="https_proxy")
        cfg = FakeConfig()
        with pytest.raises(NonRootUserError):
            action_config_unset(args, cfg=cfg)

    @pytest.mark.parametrize(
        "key,livepatch_enabled",
        (
            ("http_proxy", False),
            ("https_proxy", False),
            ("http_proxy", True),
            ("https_proxy", True),
        ),
    )
    @mock.patch("ubuntupro.livepatch.unconfigure_livepatch_proxy")
    @mock.patch(M_LIVEPATCH + "LivepatchEntitlement.application_status")
    @mock.patch("ubuntupro.snap.unconfigure_snap_proxy")
    def test_set_http_proxy_and_https_proxy_affects_snap_and_maybe_livepatch(
        self,
        unconfigure_snap_proxy,
        livepatch_status,
        unconfigure_livepatch_proxy,
        _write,
        key,
        livepatch_enabled,
        FakeConfig,
    ):
        """Set updates snap and livepatch proxy, persist config and exits 0.

        Only update livepatch proxy config is livepatch is enabled.
        """
        if livepatch_enabled:
            livepatch_status.return_value = (
                ApplicationStatus.ENABLED,
                "",
            )
        else:
            livepatch_status.return_value = (
                ApplicationStatus.DISABLED,
                "",
            )
        args = mock.MagicMock(key=key)
        cfg = FakeConfig()
        action_config_unset(args, cfg=cfg)
        assert [
            mock.call(protocol_type=key.split("_")[0])
        ] == unconfigure_snap_proxy.call_args_list
        if livepatch_enabled:
            assert [
                mock.call(protocol_type=key.split("_")[0])
            ] == unconfigure_livepatch_proxy.call_args_list
        else:
            assert [] == unconfigure_livepatch_proxy.call_args_list
