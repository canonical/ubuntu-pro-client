import mock
import pytest

from uaclient import status, util
from uaclient.cli import action_config_set, main
from uaclient.exceptions import NonRootUserError, UserFacingError

HELP_OUTPUT = """\
usage: ua set <key>=<value> [flags]

Set and apply Ubuntu Advantage configuration settings

positional arguments:
  key_value_pair  key=value pair to configure for Ubuntu Advantage services.
                  Key must be one of: http_proxy, https_proxy, apt_http_proxy,
                  apt_https_proxy, update_messaging_timer,
                  update_status_timer, metering_timer

Flags:
  -h, --help      show this help message and exit
"""

M_LIVEPATCH = "uaclient.entitlements.livepatch."


@mock.patch("uaclient.cli.os.getuid", return_value=0)
@mock.patch("uaclient.cli.setup_logging")
class TestMainConfigSet:
    @pytest.mark.parametrize(
        "kv_pair,err_msg",
        (
            ("junk", "\nExpected <key>=<value> but found: junk\n"),
            (
                "k=v",
                "<key> must be one of: http_proxy, https_proxy,"
                " apt_http_proxy, apt_https_proxy, update_messaging_timer,"
                " update_status_timer, metering_timer",
            ),
            (
                "http_proxys=",
                "<key> must be one of: http_proxy, https_proxy,"
                " apt_http_proxy, apt_https_proxy, update_messaging_timer,"
                " update_status_timer, metering_timer",
            ),
            (
                "=value",
                "<key> must be one of: http_proxy, https_proxy,"
                " apt_http_proxy, apt_https_proxy, update_messaging_timer,"
                " update_status_timer, metering_timer",
            ),
        ),
    )
    def test_set_error_with_help_on_invalid_key_value_pair(
        self, _logging, _getuid, kv_pair, err_msg, capsys
    ):
        """Exit 1 and print help on invalid key_value_pair input param."""
        with pytest.raises(SystemExit):
            with mock.patch(
                "sys.argv", ["/usr/bin/ua", "config", "set", kv_pair]
            ):
                main()
        out, err = capsys.readouterr()
        assert HELP_OUTPUT == out
        assert err_msg in err


@mock.patch("uaclient.config.UAConfig.write_cfg")
@mock.patch("uaclient.cli.os.getuid", return_value=0)
class TestActionConfigSet:
    def test_set_error_on_non_root_user(self, getuid, _write_cfg, FakeConfig):
        """Root is required to run ua config set."""
        getuid.return_value = 1
        args = mock.MagicMock(key_value_pair="something=1")
        cfg = FakeConfig()
        with pytest.raises(NonRootUserError):
            action_config_set(args, cfg=cfg)

    @pytest.mark.parametrize(
        "key,value,livepatch_enabled",
        (
            ("http_proxy", "http://proxy", False),
            ("https_proxy", "https://proxy", False),
            ("http_proxy", "http://proxy", True),
            ("https_proxy", "https://proxy", True),
        ),
    )
    @mock.patch(M_LIVEPATCH + "configure_livepatch_proxy")
    @mock.patch(M_LIVEPATCH + "LivepatchEntitlement.application_status")
    @mock.patch("uaclient.snap.configure_snap_proxy")
    @mock.patch("uaclient.util.validate_proxy")
    def test_set_http_proxy_and_https_proxy_affects_snap_and_maybe_livepatch(
        self,
        validate_proxy,
        configure_snap_proxy,
        livepatch_status,
        configure_livepatch_proxy,
        _getuid,
        _write_cfg,
        key,
        value,
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
        args = mock.MagicMock(key_value_pair="{}={}".format(key, value))
        cfg = FakeConfig()
        action_config_set(args, cfg=cfg)
        kwargs = {key: value}
        if key == "http_proxy":
            url = util.PROXY_VALIDATION_SNAP_HTTP_URL
        else:
            url = util.PROXY_VALIDATION_SNAP_HTTPS_URL
        assert [
            mock.call(key.replace("_proxy", ""), value, url)
        ] == validate_proxy.call_args_list
        assert [mock.call(**kwargs)] == configure_snap_proxy.call_args_list
        if livepatch_enabled:
            assert [
                mock.call(**kwargs)
            ] == configure_livepatch_proxy.call_args_list
        else:
            assert [] == configure_livepatch_proxy.call_args_list

    @pytest.mark.parametrize(
        "key,value",
        (
            ("apt_http_proxy", "http://proxy"),
            ("apt_https_proxy", "https://proxy"),
        ),
    )
    @mock.patch("uaclient.apt.setup_apt_proxy")
    @mock.patch("uaclient.util.validate_proxy")
    def test_set_apt_http_proxy_and_apt_https_proxy_persists_config_changes(
        self,
        validate_proxy,
        setup_apt_proxy,
        _getuid,
        _write_cfg,
        key,
        value,
        FakeConfig,
    ):
        """Set calls setup_apt_proxy, persists config and exits 0."""
        args = mock.MagicMock(key_value_pair="{}={}".format(key, value))
        cfg = FakeConfig()
        action_config_set(args, cfg=cfg)
        kwargs = {"http_proxy": None, "https_proxy": None}
        proxy_type = key.replace("apt_", "")
        kwargs[proxy_type] = value
        assert [mock.call(**kwargs)] == setup_apt_proxy.call_args_list
        if proxy_type == "http_proxy":
            url = util.PROXY_VALIDATION_APT_HTTP_URL
        else:
            url = util.PROXY_VALIDATION_APT_HTTPS_URL
        assert [
            mock.call(proxy_type.replace("_proxy", ""), value, url)
        ] == validate_proxy.call_args_list

    def test_set_timer_interval(self, _getuid, _write_cfg, FakeConfig):
        args = mock.MagicMock(key_value_pair="update_messaging_timer=28800")
        cfg = FakeConfig()
        action_config_set(args, cfg=cfg)
        assert 28800 == cfg.update_messaging_timer

    @pytest.mark.parametrize("invalid_value", ("notanumber", -1))
    def test_error_when_interval_is_not_valid(
        self, _getuid, _write_cfg, FakeConfig, invalid_value
    ):
        args = mock.MagicMock(
            key_value_pair="update_messaging_timer={}".format(invalid_value)
        )
        cfg = FakeConfig()
        with pytest.raises(UserFacingError):
            action_config_set(args, cfg=cfg)
            assert cfg.update_messaging_timer is None
