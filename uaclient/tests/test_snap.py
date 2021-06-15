"""Tests related to uaclient.snap module."""

import mock

import pytest

from uaclient import status
from uaclient.snap import configure_snap_proxy, get_config_option_value
from uaclient.util import ProcessExecutionError


class TestConfigureSnapProxy:
    @pytest.mark.parametrize(
        "http_proxy,https_proxy,snap_retries",
        (
            ("http_proxy", "https_proxy", [1, 2]),
            ("http_proxy", "", None),
            ("", "https_proxy", [1, 2]),
            ("http_proxy", None, [1, 2]),
            (None, "https_proxy", None),
            (None, None, [1, 2]),
        ),
    )
    @mock.patch("uaclient.util.subp")
    def test_configure_snap_proxy(
        self, m_subp, http_proxy, https_proxy, snap_retries, capsys
    ):
        configure_snap_proxy(http_proxy, https_proxy, snap_retries)
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
                    retry_sleeps=snap_retries,
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
                    retry_sleeps=snap_retries,
                )
            )

        assert m_subp.call_args_list == expected_calls

        out, _ = capsys.readouterr()
        if http_proxy or https_proxy:
            assert out.strip() == status.MESSAGE_SETTING_SERVICE_PROXY.format(
                service="snap"
            )

    @pytest.mark.parametrize(
        "key, subp_side_effect, expected_ret",
        [
            ("proxy.http", ProcessExecutionError("doesn't matter"), None),
            ("proxy.https", ("value", ""), "value"),
        ],
    )
    @mock.patch("uaclient.util.subp")
    def test_get_config_option_value(
        self, m_util_subp, key, subp_side_effect, expected_ret
    ):
        m_util_subp.side_effect = [subp_side_effect]
        ret = get_config_option_value(key)
        assert ret == expected_ret
        assert [
            mock.call(["snap", "get", "system", key])
        ] == m_util_subp.call_args_list
