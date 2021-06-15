"""Tests related to uaclient.livepatch module."""

import mock

try:
    from typing import Any, Dict, List  # noqa: F401
except ImportError:
    # typing isn't available on trusty, so ignore its absence
    pass


import pytest

from uaclient.livepatch import (
    configure_livepatch_proxy,
    get_config_option_value,
    configure_livepatch_proxy_with_prompts,
)


class TestConfigureLivepatchProxy:
    @pytest.mark.parametrize(
        "http_proxy,https_proxy,livepatch_retries",
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
    def test_configure_livepatch_proxy(
        self, m_subp, http_proxy, https_proxy, livepatch_retries
    ):
        configure_livepatch_proxy(http_proxy, https_proxy, livepatch_retries)
        expected_calls = []
        if http_proxy:
            expected_calls.append(
                mock.call(
                    [
                        "canonical-livepatch",
                        "config",
                        "http-proxy={}".format(http_proxy),
                    ],
                    retry_sleeps=livepatch_retries,
                )
            )

        if https_proxy:
            expected_calls.append(
                mock.call(
                    [
                        "canonical-livepatch",
                        "config",
                        "https-proxy={}".format(https_proxy),
                    ],
                    retry_sleeps=livepatch_retries,
                )
            )

        assert m_subp.call_args_list == expected_calls

    @pytest.mark.parametrize(
        "key, subp_return_value, expected_ret",
        [
            ("http-proxy", ("nonsense", ""), None),
            ("http-proxy", ("", "nonsense"), None),
            (
                "http-proxy",
                (
                    """\
http-proxy: ""
https-proxy: ""
no-proxy: ""
remote-server: https://livepatch.canonical.com
ca-certs: ""
check-interval: 60  # minutes""",
                    "",
                ),
                None,
            ),
            (
                "http-proxy",
                (
                    """\
http-proxy: one
https-proxy: two
no-proxy: ""
remote-server: https://livepatch.canonical.com
ca-certs: ""
check-interval: 60  # minutes""",
                    "",
                ),
                "one",
            ),
            (
                "https-proxy",
                (
                    """\
http-proxy: one
https-proxy: two
no-proxy: ""
remote-server: https://livepatch.canonical.com
ca-certs: ""
check-interval: 60  # minutes""",
                    "",
                ),
                "two",
            ),
            (
                "nonexistentkey",
                (
                    """\
http-proxy: one
https-proxy: two
no-proxy: ""
remote-server: https://livepatch.canonical.com
ca-certs: ""
check-interval: 60  # minutes""",
                    "",
                ),
                None,
            ),
        ],
    )
    @mock.patch("uaclient.util.subp")
    def test_get_config_option_value(
        self, m_util_subp, key, subp_return_value, expected_ret
    ):
        m_util_subp.return_value = subp_return_value
        ret = get_config_option_value(key)
        assert ret == expected_ret
        assert [
            mock.call(["canonical-livepatch", "config"])
        ] == m_util_subp.call_args_list

    @mock.patch("uaclient.livepatch.configure_livepatch_proxy")
    @mock.patch(
        "uaclient.util.prompt_for_proxy_changes",
        return_value=("prompt_ret_1", "prompt_ret_2"),
    )
    @mock.patch(
        "uaclient.livepatch.get_config_option_value",
        side_effect=["curr_ret_1", "curr_ret_2"],
    )
    def test_configure_livepatch_proxy_with_prompts(
        self,
        m_get_config_option_value,
        m_prompt_for_proxy_changes,
        m_configure_livepatch_proxy,
    ):
        configure_livepatch_proxy_with_prompts(
            http_proxy="http",
            https_proxy="https",
            livepatch_retries=[1],
            assume_yes=True,
        )
        assert [
            mock.call(
                "livepatch",
                curr_http_proxy="curr_ret_1",
                curr_https_proxy="curr_ret_2",
                new_http_proxy="http",
                new_https_proxy="https",
                assume_yes=True,
            )
        ] == m_prompt_for_proxy_changes.call_args_list
        assert [
            mock.call("prompt_ret_1", "prompt_ret_2", livepatch_retries=[1])
        ] == m_configure_livepatch_proxy.call_args_list
