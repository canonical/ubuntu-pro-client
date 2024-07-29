import mock
import pytest

from uaclient import apt, http, messages
from uaclient.cli import main
from uaclient.cli.cli_util import configure_apt_proxy
from uaclient.cli.config import set_subcommand
from uaclient.entitlements.entitlement_status import ApplicationStatus
from uaclient.exceptions import NonRootUserError, UbuntuProError

M_LIVEPATCH = "uaclient.entitlements.livepatch."


@mock.patch("uaclient.log.setup_cli_logging")
class TestMainConfigSet:
    @pytest.mark.parametrize(
        "kv_pair,err_msg",
        (
            ("junk", "\nExpected <key>=<value> but found: junk\n"),
            (
                "k=v",
                "<key> must be one of: http_proxy, https_proxy,"
                " apt_http_proxy, apt_https_proxy, ua_apt_http_proxy,"
                " ua_apt_https_proxy, global_apt_http_proxy,"
                " global_apt_https_proxy, update_messaging_timer,"
                " metering_timer",
            ),
            (
                "http_proxys=",
                "<key> must be one of: http_proxy, https_proxy,"
                " apt_http_proxy, apt_https_proxy, ua_apt_http_proxy,"
                " ua_apt_https_proxy, global_apt_http_proxy,"
                " global_apt_https_proxy, update_messaging_timer,"
                " metering_timer",
            ),
            (
                "=value",
                "<key> must be one of: http_proxy, https_proxy,"
                " apt_http_proxy, apt_https_proxy, ua_apt_http_proxy,"
                " ua_apt_https_proxy, global_apt_http_proxy,"
                " global_apt_https_proxy, update_messaging_timer,"
                " metering_timer",
            ),
            (
                "http_proxy=",
                "Empty value provided for http_proxy.",
            ),
            (
                "https_proxy=  ",
                "Empty value provided for https_proxy.",
            ),
        ),
    )
    @mock.patch("uaclient.contract.get_available_resources")
    def test_set_error_with_help_on_invalid_key_value_pair(
        self,
        _m_resources,
        _logging,
        kv_pair,
        err_msg,
        capsys,
        FakeConfig,
        event,
    ):
        """Exit 1 and print help on invalid key_value_pair input param."""
        with pytest.raises(SystemExit):
            with mock.patch(
                "sys.argv", ["/usr/bin/ua", "config", "set", kv_pair]
            ):
                with mock.patch(
                    "uaclient.config.UAConfig",
                    return_value=FakeConfig(),
                ):
                    main()
        out, err = capsys.readouterr()
        assert err_msg in err


@mock.patch("uaclient.config.user_config_file.user_config.write")
@mock.patch("uaclient.contract.get_available_resources")
class TestActionConfigSet:
    @mock.patch("uaclient.util.we_are_currently_root", return_value=False)
    def test_set_error_on_non_root_user(
        self,
        _m_resources,
        _we_are_currently_root,
        _write_,
        FakeConfig,
    ):
        """Root is required to run pro config set."""
        args = mock.MagicMock(key_value_pair="something=1")
        cfg = FakeConfig()
        with pytest.raises(NonRootUserError):
            set_subcommand.action(args, cfg=cfg)

    @pytest.mark.parametrize(
        "key,value,livepatch_enabled",
        (
            ("http_proxy", "http://proxy", False),
            ("https_proxy", "https://proxy", False),
            ("http_proxy", "http://proxy", True),
            ("https_proxy", "https://proxy", True),
        ),
    )
    @mock.patch("uaclient.cli.config.configure_livepatch_proxy")
    @mock.patch(M_LIVEPATCH + "LivepatchEntitlement.application_status")
    @mock.patch("uaclient.cli.config.configure_snap_proxy")
    @mock.patch("uaclient.http.validate_proxy")
    def test_set_http_proxy_and_https_proxy_affects_snap_and_maybe_livepatch(
        self,
        validate_proxy,
        configure_snap_proxy,
        livepatch_status,
        configure_livepatch_proxy,
        _m_resources,
        _write,
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
                ApplicationStatus.ENABLED,
                "",
            )
        else:
            livepatch_status.return_value = (
                ApplicationStatus.DISABLED,
                "",
            )
        args = mock.MagicMock(key_value_pair="{}={}".format(key, value))
        cfg = FakeConfig()
        set_subcommand.action(args, cfg=cfg)
        kwargs = {key: value}
        if key == "http_proxy":
            url = http.PROXY_VALIDATION_SNAP_HTTP_URL
        else:
            url = http.PROXY_VALIDATION_SNAP_HTTPS_URL
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
        "key,value,scope,protocol_type",
        (
            (
                "apt_http_proxy",
                "http://proxy",
                apt.AptProxyScope.GLOBAL,
                "http",
            ),
            (
                "apt_https_proxy",
                "https://proxy",
                apt.AptProxyScope.GLOBAL,
                "https",
            ),
        ),
    )
    @mock.patch("uaclient.cli.cli_util.configure_apt_proxy")
    @mock.patch("uaclient.http.validate_proxy")
    def test_set_apt_http_proxy_and_apt_https_proxy_prints_warning(
        self,
        validate_proxy,
        configure_apt_proxy,
        _m_resources,
        _write,
        key,
        value,
        scope,
        protocol_type,
        FakeConfig,
        capsys,
    ):
        """Set calls setup_apt_proxy but prints warning
        and sets global_* and exits 0."""
        args = mock.MagicMock(key_value_pair="{}={}".format(key, value))
        cfg = FakeConfig()
        set_subcommand.action(args, cfg=cfg)
        out, err = capsys.readouterr()
        global_eq = "global_" + key
        assert [
            mock.call(cfg, apt.AptProxyScope.GLOBAL, global_eq, value)
        ] == configure_apt_proxy.call_args_list
        assert (
            messages.WARNING_CONFIG_FIELD_RENAME.format(
                old="apt_{}_proxy".format(protocol_type),
                new="global_apt_{}_proxy".format(protocol_type),
            )
            in out
        )

        proxy_type = key.replace("apt_", "")
        if proxy_type == "http_proxy":
            url = http.PROXY_VALIDATION_APT_HTTP_URL
        else:
            url = http.PROXY_VALIDATION_APT_HTTPS_URL
        assert [
            mock.call(proxy_type.replace("_proxy", ""), value, url)
        ] == validate_proxy.call_args_list

        assert getattr(cfg, global_eq) == value
        assert cfg.ua_apt_https_proxy is None
        assert cfg.ua_apt_http_proxy is None

    @pytest.mark.parametrize(
        "key,value,scope,apt_equ,ua_apt_equ",
        (
            (
                "global_apt_http_proxy",
                "http://proxy",
                apt.AptProxyScope.GLOBAL,
                None,
                None,
            ),
            (
                "global_apt_https_proxy",
                "https://proxy",
                apt.AptProxyScope.GLOBAL,
                "https://proxy",
                None,
            ),
            (
                "global_apt_http_proxy",
                "https://proxy",
                apt.AptProxyScope.GLOBAL,
                "https://proxy",
                None,
            ),
            (
                "global_apt_http_proxy",
                "https://proxy",
                apt.AptProxyScope.GLOBAL,
                None,
                "https://proxy",
            ),
            (
                "global_apt_https_proxy",
                "https://proxy",
                apt.AptProxyScope.GLOBAL,
                None,
                "https://proxy",
            ),
            (
                "global_apt_https_proxy",
                "https://proxy",
                apt.AptProxyScope.GLOBAL,
                "https://proxy",
                "https://proxy",
            ),
            (
                "global_apt_http_proxy",
                "https://proxy",
                apt.AptProxyScope.GLOBAL,
                "https://proxy",
                "https://proxy",
            ),
        ),
    )
    @mock.patch("uaclient.cli.cli_util.configure_apt_proxy")
    @mock.patch("uaclient.http.validate_proxy")
    def test_set_global_apt_http_and_global_apt_https_proxy(
        self,
        validate_proxy,
        configure_apt_proxy,
        _m_resources,
        _write,
        key,
        value,
        scope,
        apt_equ,
        ua_apt_equ,
        FakeConfig,
        capsys,
    ):
        """Test setting of global_apt_* proxies"""
        args = mock.MagicMock(key_value_pair="{}={}".format(key, value))
        cfg = FakeConfig()
        cfg.ua_apt_https_proxy = ua_apt_equ
        cfg.ua_apt_http_proxy = ua_apt_equ
        set_subcommand.action(args, cfg=cfg)
        out, err = capsys.readouterr()  # will need to check output
        if ua_apt_equ:
            assert [
                mock.call(cfg, scope, key, value)
            ] == configure_apt_proxy.call_args_list
            assert (
                messages.WARNING_APT_PROXY_OVERWRITE.format(
                    current_proxy="global apt", previous_proxy="pro scoped apt"
                )
                in out
            )
        else:
            assert [
                mock.call(cfg, apt.AptProxyScope.GLOBAL, key, value)
            ] == configure_apt_proxy.call_args_list

        proxy_type = key.replace("global_apt_", "")
        if proxy_type == "http_proxy":
            url = http.PROXY_VALIDATION_APT_HTTP_URL
        else:
            url = http.PROXY_VALIDATION_APT_HTTPS_URL
        assert [
            mock.call(proxy_type.replace("_proxy", ""), value, url)
        ] == validate_proxy.call_args_list
        assert cfg.ua_apt_https_proxy is None
        assert cfg.ua_apt_http_proxy is None

    @pytest.mark.parametrize(
        "key,value,scope,apt_equ,global_apt_equ",
        (
            (
                "ua_apt_http_proxy",
                "http://proxy",
                apt.AptProxyScope.UACLIENT,
                None,
                None,
            ),
            (
                "ua_apt_https_proxy",
                "http://proxy",
                apt.AptProxyScope.UACLIENT,
                "https://proxy",
                "https://proxy",
            ),
            (
                "ua_apt_https_proxy",
                "http://proxy",
                apt.AptProxyScope.UACLIENT,
                "https://proxy",
                None,
            ),
            (
                "ua_apt_http_proxy",
                "http://proxy",
                apt.AptProxyScope.UACLIENT,
                "https://proxy",
                None,
            ),
            (
                "ua_apt_https_proxy",
                "http://proxy",
                apt.AptProxyScope.UACLIENT,
                None,
                "https://proxy",
            ),
            (
                "ua_apt_http_proxy",
                "http://proxy",
                apt.AptProxyScope.UACLIENT,
                None,
                "https://proxy",
            ),
            (
                "ua_apt_http_proxy",
                "http://proxy",
                apt.AptProxyScope.UACLIENT,
                "https://proxy",
                "https://proxy",
            ),
        ),
    )
    @mock.patch("uaclient.cli.cli_util.configure_apt_proxy")
    @mock.patch("uaclient.http.validate_proxy")
    def test_set_ua_apt_http_and_ua_apt_https_proxy(
        self,
        validate_proxy,
        configure_apt_proxy,
        _m_resources,
        _write,
        key,
        value,
        scope,
        apt_equ,
        global_apt_equ,
        FakeConfig,
        capsys,
    ):
        """Test setting of ua_apt_* proxies"""
        args = mock.MagicMock(key_value_pair="{}={}".format(key, value))
        cfg = FakeConfig()
        cfg.global_apt_http_proxy = global_apt_equ
        cfg.global_apt_https_proxy = global_apt_equ
        set_subcommand.action(args, cfg=cfg)
        out, err = capsys.readouterr()  # will need to check output
        if global_apt_equ:
            assert [
                mock.call(cfg, scope, key, value)
            ] == configure_apt_proxy.call_args_list
            assert (
                messages.WARNING_APT_PROXY_OVERWRITE.format(
                    current_proxy="pro scoped apt", previous_proxy="global apt"
                )
                in out
            )
        else:
            assert [
                mock.call(cfg, apt.AptProxyScope.UACLIENT, key, value)
            ] == configure_apt_proxy.call_args_list

        proxy_type = key.replace("ua_apt_", "")
        if proxy_type == "http_proxy":
            url = http.PROXY_VALIDATION_APT_HTTP_URL
        else:
            url = http.PROXY_VALIDATION_APT_HTTPS_URL
        assert [
            mock.call(proxy_type.replace("_proxy", ""), value, url)
        ] == validate_proxy.call_args_list
        assert cfg.global_apt_https_proxy is None
        assert cfg.global_apt_http_proxy is None

    @pytest.mark.parametrize(
        "key,value,scope",
        (
            (
                "global_apt_https_proxy",
                "http://proxy",
                apt.AptProxyScope.GLOBAL,
            ),
            (
                "global_apt_http_proxy",
                "https://proxy",
                apt.AptProxyScope.GLOBAL,
            ),
            ("global_apt_https_proxy", None, apt.AptProxyScope.GLOBAL),
        ),
    )
    @mock.patch("uaclient.cli.cli_util.setup_apt_proxy")
    def test_configure_global_apt_proxy(
        self,
        setup_apt_proxy,
        _m_resources,
        _write,
        key,
        value,
        scope,
        FakeConfig,
    ):
        cfg = FakeConfig()
        cfg.global_apt_http_proxy = value
        cfg.global_apt_https_proxy = value
        configure_apt_proxy(cfg, scope, key, value)
        kwargs = {
            "http_proxy": cfg.global_apt_http_proxy,
            "https_proxy": cfg.global_apt_https_proxy,
            "proxy_scope": scope,
        }
        assert 1 == setup_apt_proxy.call_count
        assert [mock.call(**kwargs)] == setup_apt_proxy.call_args_list

    @pytest.mark.parametrize(
        "key,value,scope",
        (
            (
                "global_apt_https_proxy",
                "http://proxy",
                apt.AptProxyScope.UACLIENT,
            ),
            (
                "global_apt_http_proxy",
                "https://proxy",
                apt.AptProxyScope.UACLIENT,
            ),
            ("global_apt_https_proxy", None, apt.AptProxyScope.UACLIENT),
        ),
    )
    @mock.patch("uaclient.cli.cli_util.setup_apt_proxy")
    def test_configure_uaclient_apt_proxy(
        self,
        setup_apt_proxy,
        _m_resources,
        _write,
        key,
        value,
        scope,
        FakeConfig,
    ):
        cfg = FakeConfig()
        cfg.ua_apt_http_proxy = value
        cfg.ua_apt_https_proxy = value
        configure_apt_proxy(cfg, scope, key, value)
        kwargs = {
            "http_proxy": cfg.ua_apt_http_proxy,
            "https_proxy": cfg.ua_apt_https_proxy,
            "proxy_scope": scope,
        }
        assert 1 == setup_apt_proxy.call_count
        assert [mock.call(**kwargs)] == setup_apt_proxy.call_args_list

    def test_set_timer_interval(self, _m_resources, _write, FakeConfig):
        args = mock.MagicMock(key_value_pair="update_messaging_timer=28800")
        cfg = FakeConfig()
        set_subcommand.action(args, cfg=cfg)
        assert 28800 == cfg.update_messaging_timer

    @pytest.mark.parametrize("invalid_value", ("notanumber", -1))
    def test_error_when_interval_is_not_valid(
        self,
        _m_resources,
        _write,
        FakeConfig,
        invalid_value,
    ):
        args = mock.MagicMock(
            key_value_pair="update_messaging_timer={}".format(invalid_value)
        )
        cfg = FakeConfig()
        with pytest.raises(UbuntuProError):
            set_subcommand.action(args, cfg=cfg)
            assert cfg.update_messaging_timer is None
