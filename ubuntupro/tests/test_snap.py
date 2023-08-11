"""Tests related to ubuntupro.snap module."""

import mock
import pytest

from ubuntupro import exceptions, messages
from ubuntupro.snap import (
    SnapPackage,
    configure_snap_proxy,
    get_config_option_value,
    get_installed_snaps,
    get_snap_info,
    unconfigure_snap_proxy,
)


class TestConfigureSnapProxy:
    @pytest.mark.parametrize("http_proxy", ("http_proxy", "", None))
    @pytest.mark.parametrize("https_proxy", ("https_proxy", "", None))
    @pytest.mark.parametrize("snapd_installed", (True, False))
    @mock.patch("ubuntupro.system.subp")
    @mock.patch("ubuntupro.snap.is_snapd_installed")
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
    @mock.patch("ubuntupro.system.subp")
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
    @mock.patch("ubuntupro.system.subp")
    @mock.patch("ubuntupro.snap.is_snapd_installed")
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
    @mock.patch("ubuntupro.snap.get_snap_info")
    @mock.patch("ubuntupro.snap.system.subp")
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
    @mock.patch("socket.socket")
    @mock.patch("http.client.HTTPConnection")
    def test_get_snap_info_error_parsing_json(
        self, m_http_connection, m_socket
    ):
        socket_mock = mock.MagicMock()
        m_socket.return_value = socket_mock
        http_mock = mock.MagicMock()
        http_response_mock = mock.MagicMock()
        http_mock.getresponse.return_value = http_response_mock
        http_response_mock.read.return_value = b"invalid-json"
        m_http_connection.return_value = http_mock

        with pytest.raises(exceptions.SnapdInvalidJson):
            get_snap_info(snap="test")

        assert 1 == m_http_connection.call_count
        assert 1 == http_mock.getresponse.call_count
        assert 1 == http_response_mock.read.call_count
        assert 1 == http_response_mock.read.call_count
        assert 1 == http_response_mock.read.call_count
        assert 1 == socket_mock.close.call_count
        assert 1 == http_mock.close.call_count

    @pytest.mark.parametrize(
        "status_code,response_data,expected_exception",
        (
            (
                404,
                b'{"result": {"kind": "snap-not-found"}}',
                exceptions.SnapNotInstalledError,
            ),
            (
                404,
                b'{"result": {"kind": ""}}',
                exceptions.UnexpectedSnapdAPIError,
            ),
            (
                500,
                b'{"result": {"message": "error"}}',
                exceptions.UnexpectedSnapdAPIError,
            ),
            (
                401,
                b"{}",
                exceptions.UnexpectedSnapdAPIError,
            ),
        ),
    )
    @mock.patch("socket.socket")
    @mock.patch("http.client.HTTPConnection")
    def test_get_snap_info_unexpected_api_error(
        self,
        m_http_connection,
        m_socket,
        status_code,
        response_data,
        expected_exception,
    ):
        socket_mock = mock.MagicMock()
        m_socket.return_value = socket_mock
        http_mock = mock.MagicMock()
        http_response_mock = mock.MagicMock(status=status_code)
        http_mock.getresponse.return_value = http_response_mock
        http_response_mock.read.return_value = response_data
        m_http_connection.return_value = http_mock

        with pytest.raises(expected_exception):
            get_snap_info(snap="test")

        assert 1 == m_http_connection.call_count
        assert 1 == http_mock.getresponse.call_count
        assert 1 == http_response_mock.read.call_count
        assert 1 == socket_mock.close.call_count
        assert 1 == http_mock.close.call_count

    @mock.patch("socket.socket")
    @mock.patch("http.client.HTTPConnection")
    def test_get_snap_info_connection_refused(
        self,
        m_http_connection,
        m_socket,
    ):
        socket_mock = mock.MagicMock()
        m_socket.return_value = socket_mock
        http_mock = mock.MagicMock()
        http_mock.request.side_effect = ConnectionRefusedError()
        m_http_connection.return_value = http_mock

        with pytest.raises(exceptions.SnapdAPIConnectionRefused):
            get_snap_info(snap="test")

        assert 1 == m_http_connection.call_count
        assert 1 == http_mock.request.call_count
        assert 1 == socket_mock.close.call_count
        assert 1 == http_mock.close.call_count

    @mock.patch("socket.socket")
    @mock.patch("http.client.HTTPConnection")
    def test_get_snap_info(
        self,
        m_http_connection,
        m_socket,
    ):
        socket_mock = mock.MagicMock()
        m_socket.return_value = socket_mock
        http_mock = mock.MagicMock()
        http_response_mock = mock.MagicMock(status=200)
        http_mock.getresponse.return_value = http_response_mock
        http_response_mock.read.return_value = b'{"result": {"channel": "stable", "revision": "120", "name": "test", "publisher": {"username": "canonical"}}}'  # noqa
        m_http_connection.return_value = http_mock

        expected_result = SnapPackage(
            name="test",
            version="",
            revision="120",
            channel="stable",
            publisher="canonical",
        )
        assert expected_result == get_snap_info(snap="test")

        assert 1 == m_http_connection.call_count
        assert 1 == http_mock.getresponse.call_count
        assert 1 == http_response_mock.read.call_count
        assert 1 == socket_mock.close.call_count
        assert 1 == http_mock.close.call_count
