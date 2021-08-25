import mock
import pytest

from uaclient import status
from uaclient.cli import action_config_unset, main
from uaclient.exceptions import NonRootUserError

HELP_OUTPUT = """\
usage: ua unset <key> [flags]

Unset Ubuntu Advantage configuration setting

positional arguments:
  key         configuration key to unset from Ubuntu Advantage services. One
              of: http_proxy, https_proxy, apt_http_proxy, apt_https_proxy,
              update_messaging_timer, update_status_timer,
              gcp_auto_attach_timer, metering_timer

Flags:
  -h, --help  show this help message and exit
"""

M_LIVEPATCH = "uaclient.entitlements.livepatch."


@mock.patch("uaclient.cli.os.getuid", return_value=0)
@mock.patch("uaclient.cli.setup_logging")
class TestMainConfigUnSet:
    @pytest.mark.parametrize(
        "kv_pair,err_msg",
        (
            (
                "junk",
                "<key> must be one of: http_proxy, https_proxy,"
                " apt_http_proxy, apt_https_proxy, update_messaging_timer, "
                "update_status_timer, gcp_auto_attach_timer, metering_timer",
            ),
            (
                "http_proxys",
                "<key> must be one of: http_proxy, https_proxy,"
                " apt_http_proxy, apt_https_proxy, update_messaging_timer, "
                "update_status_timer, gcp_auto_attach_timer, metering_timer",
            ),
        ),
    )
    def test_set_error_with_help_on_invalid_key_value_pair(
        self, _logging, _getuid, kv_pair, err_msg, capsys
    ):
        """Exit 1 and print help on invalid key_value_pair input param."""
        with pytest.raises(SystemExit):
            with mock.patch(
                "sys.argv", ["/usr/bin/ua", "config", "unset", kv_pair]
            ):
                main()
        out, err = capsys.readouterr()
        assert HELP_OUTPUT == out
        assert err_msg in err


@mock.patch("uaclient.config.UAConfig.write_cfg")
@mock.patch("uaclient.cli.os.getuid", return_value=0)
class TestActionConfigUnSet:
    def test_set_error_on_non_root_user(self, getuid, _write_cfg, FakeConfig):
        """Root is required to run ua config unset."""
        getuid.return_value = 1
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
    @mock.patch(M_LIVEPATCH + "unconfigure_livepatch_proxy")
    @mock.patch(M_LIVEPATCH + "LivepatchEntitlement.application_status")
    @mock.patch("uaclient.snap.unconfigure_snap_proxy")
    def test_set_http_proxy_and_https_proxy_affects_snap_and_maybe_livepatch(
        self,
        unconfigure_snap_proxy,
        livepatch_status,
        unconfigure_livepatch_proxy,
        _getuid,
        _write_cfg,
        key,
        livepatch_enabled,
        FakeConfig,
    ):
        """Set updates snap and livepatch proxy, persist config and exits 0.

        Only update livepatch proxy config is livepatch is enabled.
        """
        if livepatch_enabled:
            livepatch_status.return_value = (
                status.ApplicationStatus.ENABLED,
                "",
            )
        else:
            livepatch_status.return_value = (
                status.ApplicationStatus.DISABLED,
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
