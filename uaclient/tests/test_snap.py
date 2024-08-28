"""Tests related to uaclient.snap module."""

import mock
import pytest

from uaclient import exceptions, messages
from uaclient.snap import (
    SnapPackage,
    configure_snap_proxy,
    get_config_option_value,
    get_installed_snaps,
    get_snap_info,
    is_snapd_installed_as_a_snap,
    unconfigure_snap_proxy,
)


class TestIsSnapdInstalledAsASnap:
    @pytest.mark.parametrize(
        ["installed_snaps", "expected"],
        [
            ([], False),
            (
                [
                    SnapPackage(
                        "one", "123", "456", "oldest/unstable", "someone"
                    )
                ],
                False,
            ),
            (
                [
                    SnapPackage(
                        "snapd", "123", "456", "oldest/unstable", "someone"
                    )
                ],
                True,
            ),
            (
                [
                    SnapPackage(
                        "one", "123", "456", "oldest/unstable", "someone"
                    ),
                    SnapPackage(
                        "snapd", "123", "456", "oldest/unstable", "someone"
                    ),
                ],
                True,
            ),
        ],
    )
    @mock.patch("uaclient.snap.get_installed_snaps")
    def test_is_snapd_installed_as_a_snap(
        self, m_get_installed_snaps, installed_snaps, expected
    ):
        m_get_installed_snaps.return_value = installed_snaps
        assert expected == is_snapd_installed_as_a_snap()


class TestConfigureSnapProxy:
    @pytest.mark.parametrize("http_proxy", ("http_proxy", "", None))
    @pytest.mark.parametrize("https_proxy", ("https_proxy", "", None))
    @pytest.mark.parametrize("snapd_installed", (True, False))
    @mock.patch("uaclient.system.subp")
    @mock.patch("uaclient.snap.is_snapd_installed")
    def test_configure_snap_proxy(
        self,
        m_is_snapd_installed,
        m_subp,
        http_proxy,
        https_proxy,
        snapd_installed,
        capsys,
    ):
        retry_sleeps = mock.MagicMock()
        m_is_snapd_installed.return_value = snapd_installed
        configure_snap_proxy(http_proxy, https_proxy, retry_sleeps)
        expected_calls = []
        if snapd_installed:
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
        assert 1 == m_is_snapd_installed.call_count

        out, _ = capsys.readouterr()
        if snapd_installed and (http_proxy or https_proxy):
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
    @pytest.mark.parametrize("protocol_type", ("http", "https"))
    @pytest.mark.parametrize("retry_sleeps", (None, [1], []))
    @pytest.mark.parametrize("snapd_installed", (True, False))
    @mock.patch("uaclient.system.subp")
    @mock.patch("uaclient.snap.is_snapd_installed")
    def test_unconfigure_snap_proxy(
        self,
        m_snapd_installed,
        m_subp,
        protocol_type,
        retry_sleeps,
        snapd_installed,
    ):
        m_snapd_installed.return_value = snapd_installed
        subp_calls = []
        if snapd_installed:
            subp_calls = [
                mock.call(
                    ["snap", "unset", "system", "proxy." + protocol_type],
                    retry_sleeps=retry_sleeps,
                )
            ]

        kwargs = {"protocol_type": protocol_type}
        if retry_sleeps is not None:
            kwargs["retry_sleeps"] = retry_sleeps
        assert None is unconfigure_snap_proxy(**kwargs)
        assert 1 == m_snapd_installed.call_count
        assert subp_calls == m_subp.call_args_list


class TestSnapPackagesInstalled:
    @mock.patch("uaclient.snap.get_snap_info")
    @mock.patch("uaclient.snap.system.subp")
    def test_snap_packages_installed(self, m_sys_subp, m_get_snap_info):
        m_sys_subp.return_value = (
            "Name  Version Rev Tracking Publisher Notes\n"
            "helloworld 6.0.16 126 latest/stable dev1 -\n"
            "bare 1.0 5 latest/stable canonical** base\n"
            "canonical-livepatch 10.2.3 146 latest/stable canonical** -\n"
        ), ""
        expected_snaps = [
            SnapPackage(
                "helloworld",
                "6.0.16",
                "126",
                "latest/stable",
                "dev1",
            ),
            SnapPackage(
                "bare",
                "1.0",
                "5",
                "latest/stable",
                "canonical**",
            ),
            SnapPackage(
                "canonical-livepatch",
                "10.2.3",
                "146",
                "latest/stable",
                "canonical**",
            ),
        ]
        m_get_snap_info.side_effect = expected_snaps
        snaps = get_installed_snaps()
        assert snaps[0].name == expected_snaps[0].name
        assert snaps[0].revision == expected_snaps[0].revision
        assert snaps[1].name == expected_snaps[1].name
        assert snaps[1].publisher == expected_snaps[1].publisher
        assert snaps[2].channel == expected_snaps[2].channel


class TestGetSnapInfo:
    @pytest.mark.parametrize(
        "status_code,response_data,expected_exception",
        (
            (
                404,
                {"result": {"kind": "snap-not-found"}},
                exceptions.SnapNotInstalledError,
            ),
            (
                404,
                {"result": {"kind": ""}},
                exceptions.UnexpectedSnapdAPIError,
            ),
            (
                500,
                {"result": {"message": "error"}},
                exceptions.UnexpectedSnapdAPIError,
            ),
            (
                401,
                {},
                exceptions.UnexpectedSnapdAPIError,
            ),
        ),
    )
    @mock.patch("uaclient.snap.http.unix_socket_request")
    def test_get_snap_info_unexpected_api_error(
        self,
        m_unix_socket_request,
        status_code,
        response_data,
        expected_exception,
    ):
        m_unix_socket_request.return_value = mock.MagicMock(
            code=status_code, json_dict=response_data
        )

        with pytest.raises(expected_exception):
            get_snap_info(snap="test")

        assert 1 == m_unix_socket_request.call_count

    @mock.patch("uaclient.snap.http.unix_socket_request")
    def test_get_snap_info_connection_refused(
        self,
        m_unix_socket_request,
    ):
        m_unix_socket_request.side_effect = ConnectionRefusedError()

        with pytest.raises(exceptions.SnapdAPIConnectionRefused):
            get_snap_info(snap="test")

        assert 1 == m_unix_socket_request.call_count

    @mock.patch("uaclient.snap.http.unix_socket_request")
    def test_get_snap_info(
        self,
        m_unix_socket_request,
    ):
        m_unix_socket_request.return_value = mock.MagicMock(
            code=200,
            json_dict={
                "result": {
                    "channel": "stable",
                    "revision": "120",
                    "name": "test",
                    "publisher": {"username": "canonical"},
                }
            },
        )

        expected_result = SnapPackage(
            name="test",
            version="",
            revision="120",
            channel="stable",
            publisher="canonical",
        )
        assert expected_result == get_snap_info(snap="test")

        assert 1 == m_unix_socket_request.call_count
