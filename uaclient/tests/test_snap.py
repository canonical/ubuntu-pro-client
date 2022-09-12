"""Tests related to uaclient.snap module."""

import mock
import pytest

from uaclient import exceptions, messages
from uaclient.snap import (
    SnapPackage,
    configure_snap_proxy,
    get_config_option_value,
    get_installed_snaps,
    get_snap_package_info_tracking,
    unconfigure_snap_proxy,
)


class TestConfigureSnapProxy:
    @pytest.mark.parametrize(
        "http_proxy,https_proxy,retry_sleeps",
        (
            ("http_proxy", "https_proxy", [1, 2]),
            ("http_proxy", "", None),
            ("", "https_proxy", [1, 2]),
            ("http_proxy", None, [1, 2]),
            (None, "https_proxy", None),
            (None, None, [1, 2]),
        ),
    )
    @mock.patch("uaclient.system.subp")
    @mock.patch("uaclient.system.which", return_value=True)
    def test_configure_snap_proxy(
        self, m_which, m_subp, http_proxy, https_proxy, retry_sleeps, capsys
    ):
        configure_snap_proxy(http_proxy, https_proxy, retry_sleeps)
        expected_calls = []
        if http_proxy:
            expected_calls.append(
                mock.call(
                    [
                        "snap",
                        "set",
                        "system",
                        "proxy.http={}".format(http_proxy),
                    ],
                    retry_sleeps=retry_sleeps,
                )
            )

        if https_proxy:
            expected_calls.append(
                mock.call(
                    [
                        "snap",
                        "set",
                        "system",
                        "proxy.https={}".format(https_proxy),
                    ],
                    retry_sleeps=retry_sleeps,
                )
            )

        assert m_subp.call_args_list == expected_calls

        out, _ = capsys.readouterr()
        if http_proxy or https_proxy:
            assert out.strip() == messages.SETTING_SERVICE_PROXY.format(
                service="snap"
            )

    @pytest.mark.parametrize(
        "key, subp_side_effect, expected_ret",
        [
            (
                "proxy.http",
                exceptions.ProcessExecutionError("doesn't matter"),
                None,
            ),
            ("proxy.https", ("value", ""), "value"),
        ],
    )
    @mock.patch("uaclient.system.subp")
    def test_get_config_option_value(
        self, m_util_subp, key, subp_side_effect, expected_ret
    ):
        m_util_subp.side_effect = [subp_side_effect]
        ret = get_config_option_value(key)
        assert ret == expected_ret
        assert [
            mock.call(["snap", "get", "system", key])
        ] == m_util_subp.call_args_list


class TestUnconfigureSnapProxy:
    @pytest.mark.parametrize(
        "snap_installed, protocol_type, retry_sleeps",
        ((True, "http", None), (True, "https", [1]), (True, "http", [])),
    )
    @mock.patch("uaclient.system.subp")
    @mock.patch("uaclient.system.which")
    def test_unconfigure_snap_proxy(
        self, which, subp, snap_installed, protocol_type, retry_sleeps
    ):
        if snap_installed:
            which.return_value = "/usr/bin/snap"
            subp_calls = [
                mock.call(
                    ["snap", "unset", "system", "proxy." + protocol_type],
                    retry_sleeps=retry_sleeps,
                )
            ]
        else:
            which.return_value = None
            subp_calls = []
        kwargs = {"protocol_type": protocol_type}
        if retry_sleeps is not None:
            kwargs["retry_sleeps"] = retry_sleeps
        assert None is unconfigure_snap_proxy(**kwargs)
        assert [mock.call("/usr/bin/snap")] == which.call_args_list
        assert subp_calls == subp.call_args_list


@mock.patch("uaclient.snap.system.subp")
class TestSnapPackagesInstalled:
    def test_snap_packages_installed(self, sys_subp):
        sys_subp.return_value = (
            "Name  Version Rev Tracking Publisher Notes\n"
            "helloworld 6.0.16 126 latest/stable dev1 -\n"
            "bare 1.0 5 latest/stable canonical** base\n"
            "canonical-livepatch 10.2.3 146 latest/stable canonical** -\n"
        ), ""
        expected_snaps = [
            SnapPackage(
                "helloworld", "6.0.16", "126", "latest/stable", "dev1", "-"
            ),
            SnapPackage(
                "bare", "1.0", "5", "latest/stable", "canonical**", "base"
            ),
            SnapPackage(
                "canonical-livepatch",
                "10.2.3",
                "146",
                "latest/stable",
                "canonical**",
                "-",
            ),
        ]
        snaps = get_installed_snaps()
        assert snaps[0].name == expected_snaps[0].name
        assert snaps[0].rev == expected_snaps[0].rev
        assert snaps[1].name == expected_snaps[1].name
        assert snaps[1].publisher == expected_snaps[1].publisher
        assert snaps[2].tracking == expected_snaps[2].tracking
        assert snaps[2].notes == expected_snaps[2].notes

    @pytest.mark.parametrize(
        "subp_ret,channel_ret",
        [
            (
                """snap-id: ID001
                   tracking: latest/stable
                """,
                "latest/stable",
            ),
            (
                """snap-id: ID001
                """,
                None,
            ),
        ],
    )
    def test_snap_package_info_tracking(self, sys_subp, subp_ret, channel_ret):
        sys_subp.return_value = subp_ret, ""
        channel = get_snap_package_info_tracking("test")
        assert channel == channel_ret
