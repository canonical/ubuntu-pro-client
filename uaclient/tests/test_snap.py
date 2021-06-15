"""Tests related to uaclient.snap module."""

import mock

import pytest

from uaclient.snap import (
    configure_snap_proxy,
    get_config_option_value,
    configure_snap_proxy_with_prompts,
)
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
        self, m_subp, http_proxy, https_proxy, snap_retries
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

    @mock.patch("uaclient.snap.configure_snap_proxy")
    @mock.patch(
        "uaclient.util.prompt_for_proxy_changes",
        return_value=("prompt_ret_1", "prompt_ret_2"),
    )
    @mock.patch(
        "uaclient.snap.get_config_option_value",
        side_effect=["curr_ret_1", "curr_ret_2"],
    )
    def test_configure_snap_proxy_with_prompts(
        self,
        m_get_config_option_value,
        m_prompt_for_proxy_changes,
        m_configure_snap_proxy,
    ):
        configure_snap_proxy_with_prompts(
            http_proxy="http",
            https_proxy="https",
            snap_retries=[1],
            assume_yes=True,
        )
        assert [
            mock.call(
                "snap",
                curr_http_proxy="curr_ret_1",
                curr_https_proxy="curr_ret_2",
                new_http_proxy="http",
                new_https_proxy="https",
                assume_yes=True,
            )
        ] == m_prompt_for_proxy_changes.call_args_list
        assert [
            mock.call("prompt_ret_1", "prompt_ret_2", snap_retries=[1])
        ] == m_configure_snap_proxy.call_args_list
