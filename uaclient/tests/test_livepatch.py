import datetime
import json

import mock
import pytest

from uaclient import exceptions, messages, system
from uaclient.entitlements.livepatch import LivepatchEntitlement
from uaclient.files.state_files import LivepatchSupportCacheData
from uaclient.livepatch import (
    LIVEPATCH_CMD,
    LivepatchPatchFixStatus,
    LivepatchPatchStatus,
    LivepatchStatusStatus,
    LivepatchSupport,
    UALivepatchClient,
    _on_supported_kernel_api,
    _on_supported_kernel_cache,
    _on_supported_kernel_cli,
    configure_livepatch_proxy,
    get_config_option_value,
    on_supported_kernel,
    status,
    unconfigure_livepatch_proxy,
)

M_PATH = "uaclient.livepatch."


class TestStatus:
    @pytest.mark.parametrize(
        [
            "is_installed",
            "subp_sideeffect",
            "expected",
        ],
        [
            (False, None, None),
            (True, exceptions.ProcessExecutionError(""), None),
            (True, [("", None)], None),
            (True, [("{", None)], None),
            (True, [("{}", None)], None),
            (True, [('{"Status": false}', None)], None),
            (True, [('{"Status": []}', None)], None),
            (
                True,
                [('{"Status": [{}]}', None)],
                LivepatchStatusStatus(
                    kernel=None, livepatch=None, supported=None
                ),
            ),
            (
                True,
                [
                    (
                        json.dumps(
                            {
                                "Status": [
                                    {
                                        "Kernel": "installed-kernel-generic",
                                        "Livepatch": {
                                            "State": "nothing-to-apply",
                                            "Version": "100",
                                        },
                                    }
                                ],
                            }
                        ),
                        None,
                    )
                ],
                LivepatchStatusStatus(
                    kernel="installed-kernel-generic",
                    livepatch=LivepatchPatchStatus(
                        state="nothing-to-apply",
                        fixes=None,
                        version="100",
                    ),
                    supported=None,
                ),
            ),
            (
                True,
                [
                    (
                        json.dumps(
                            {
                                "Status": [
                                    {
                                        "Kernel": "installed-kernel-generic",
                                        "Livepatch": {
                                            "State": "applied",
                                            "Fixes": [
                                                {
                                                    "Name": "cve-example",
                                                    "Description": "",
                                                    "Bug": "",
                                                    "Patched": True,
                                                },
                                            ],
                                        },
                                    }
                                ],
                            }
                        ),
                        None,
                    )
                ],
                LivepatchStatusStatus(
                    kernel="installed-kernel-generic",
                    livepatch=LivepatchPatchStatus(
                        state="applied",
                        fixes=[
                            LivepatchPatchFixStatus(
                                name="cve-example",
                                patched=True,
                            )
                        ],
                        version=None,
                    ),
                    supported=None,
                ),
            ),
            (
                True,
                [
                    (
                        json.dumps(
                            {
                                "Client-Version": "version",
                                "Machine-Id": "machine-id",
                                "Architecture": "x86_64",
                                "CPU-Model": "Intel(R) Core(TM) i7-8650U CPU @ 1.90GHz",  # noqa: E501
                                "Last-Check": "2022-07-05T18:29:00Z",
                                "Boot-Time": "2022-07-05T18:27:12Z",
                                "Uptime": "203",
                                "Status": [
                                    {
                                        "Kernel": "4.15.0-187.198-generic",
                                        "Running": True,
                                        "Livepatch": {
                                            "CheckState": "checked",
                                            "State": "nothing-to-apply",
                                            "Version": "",
                                        },
                                    }
                                ],
                                "tier": "stable",
                            }
                        ),
                        None,
                    )
                ],
                LivepatchStatusStatus(
                    kernel="4.15.0-187.198-generic",
                    livepatch=LivepatchPatchStatus(
                        state="nothing-to-apply", fixes=None, version=""
                    ),
                    supported=None,
                ),
            ),
            (
                True,
                [
                    (
                        json.dumps(
                            {
                                "Status": [
                                    {
                                        "Supported": "supported",
                                    }
                                ],
                            }
                        ),
                        None,
                    )
                ],
                LivepatchStatusStatus(
                    kernel=None,
                    livepatch=None,
                    supported="supported",
                ),
            ),
        ],
    )
    @mock.patch(M_PATH + "system.subp")
    @mock.patch(M_PATH + "is_livepatch_installed")
    def test_status(
        self,
        m_is_livepatch_installed,
        m_subp,
        is_installed,
        subp_sideeffect,
        expected,
    ):
        m_is_livepatch_installed.return_value = is_installed
        m_subp.side_effect = subp_sideeffect
        assert expected == status()


@mock.patch(M_PATH + "serviceclient.UAServiceClient.request_url")
@mock.patch(M_PATH + "serviceclient.UAServiceClient.headers")
class TestUALivepatchClient:
    @pytest.mark.parametrize(
        [
            "version",
            "flavor",
            "arch",
            "codename",
            "expected_request_calls",
        ],
        [
            (
                "1.23-4",
                "generic",
                "amd64",
                "xenial",
                [
                    mock.call(
                        "/v1/api/kernels/supported",
                        headers=mock.ANY,
                        query_params={
                            "kernel-version": "1.23-4",
                            "flavour": "generic",
                            "architecture": "amd64",
                            "codename": "xenial",
                        },
                    )
                ],
            ),
            (
                "5.67-8",
                "kvm",
                "arm64",
                "kinetic",
                [
                    mock.call(
                        "/v1/api/kernels/supported",
                        headers=mock.ANY,
                        query_params={
                            "kernel-version": "5.67-8",
                            "flavour": "kvm",
                            "architecture": "arm64",
                            "codename": "kinetic",
                        },
                    )
                ],
            ),
        ],
    )
    def test_is_kernel_supported_calls_api_with_correct_params(
        self,
        m_headers,
        m_request_url,
        version,
        flavor,
        arch,
        codename,
        expected_request_calls,
    ):
        m_request_url.return_value = ("mock", "mock")
        lp_client = UALivepatchClient()
        lp_client.is_kernel_supported(version, flavor, arch, codename)
        assert m_request_url.call_args_list == expected_request_calls

    @pytest.mark.parametrize(
        [
            "request_side_effect",
            "expected",
        ],
        [
            ([({"Supported": True}, None)], True),
            ([({"Supported": False}, None)], False),
            ([({}, None)], False),
            ([([], None)], None),
            ([("string", None)], None),
            (exceptions.UrlError(mock.MagicMock()), None),
            (Exception(), None),
        ],
    )
    def test_is_kernel_supported_interprets_api_response(
        self,
        m_headers,
        m_request_url,
        request_side_effect,
        expected,
    ):
        m_request_url.side_effect = request_side_effect
        lp_client = UALivepatchClient()
        assert lp_client.is_kernel_supported("", "", "", "") == expected


class TestOnSupportedKernel:
    @pytest.mark.parametrize(
        [
            "livepatch_status",
            "expected",
        ],
        [
            (None, None),
            (
                LivepatchStatusStatus(
                    kernel=None, livepatch=None, supported=None
                ),
                None,
            ),
            (
                LivepatchStatusStatus(
                    kernel=None, livepatch=None, supported="supported"
                ),
                LivepatchSupport.SUPPORTED,
            ),
            (
                LivepatchStatusStatus(
                    kernel=None, livepatch=None, supported="unsupported"
                ),
                LivepatchSupport.UNSUPPORTED,
            ),
            (
                LivepatchStatusStatus(
                    kernel=None,
                    livepatch=None,
                    supported="kernel-upgrade-required",
                ),
                LivepatchSupport.KERNEL_UPGRADE_REQUIRED,
            ),
            (
                LivepatchStatusStatus(
                    kernel=None, livepatch=None, supported="kernel-end-of-life"
                ),
                LivepatchSupport.KERNEL_EOL,
            ),
            (
                LivepatchStatusStatus(
                    kernel=None, livepatch=None, supported="unknown"
                ),
                LivepatchSupport.UNKNOWN,
            ),
        ],
    )
    @mock.patch(M_PATH + "status")
    def test_on_supported_kernel_cli(
        self,
        m_livepatch_status,
        livepatch_status,
        expected,
    ):
        m_livepatch_status.return_value = livepatch_status
        assert _on_supported_kernel_cli() == expected

    @pytest.mark.parametrize(
        [
            "args",
            "cache_contents",
            "expected",
        ],
        [
            # valid true
            (
                ("5.14-14", "generic", "amd64", "focal"),
                LivepatchSupportCacheData(
                    version="5.14-14",
                    flavor="generic",
                    arch="amd64",
                    codename="focal",
                    cached_at=datetime.datetime.now(datetime.timezone.utc)
                    - datetime.timedelta(days=6),
                    supported=True,
                ),
                (True, True),
            ),
            # valid false
            (
                ("5.14-14", "generic", "amd64", "focal"),
                LivepatchSupportCacheData(
                    version="5.14-14",
                    flavor="generic",
                    arch="amd64",
                    codename="focal",
                    cached_at=datetime.datetime.now(datetime.timezone.utc)
                    - datetime.timedelta(days=6),
                    supported=False,
                ),
                (True, False),
            ),
            # valid none
            (
                ("5.14-14", "generic", "amd64", "focal"),
                LivepatchSupportCacheData(
                    version="5.14-14",
                    flavor="generic",
                    arch="amd64",
                    codename="focal",
                    cached_at=datetime.datetime.now(datetime.timezone.utc)
                    - datetime.timedelta(days=6),
                    supported=None,
                ),
                (True, None),
            ),
            # invalid version doesn't match
            (
                ("5.14-13", "generic", "amd64", "focal"),
                LivepatchSupportCacheData(
                    version="5.14-14",
                    flavor="generic",
                    arch="amd64",
                    codename="focal",
                    cached_at=datetime.datetime.now(datetime.timezone.utc)
                    - datetime.timedelta(days=6),
                    supported=True,
                ),
                (False, None),
            ),
            # invalid flavor doesn't match
            (
                ("5.14-14", "kvm", "amd64", "focal"),
                LivepatchSupportCacheData(
                    version="5.14-14",
                    flavor="generic",
                    arch="amd64",
                    codename="focal",
                    cached_at=datetime.datetime.now(datetime.timezone.utc)
                    - datetime.timedelta(days=6),
                    supported=True,
                ),
                (False, None),
            ),
            # invalid arch doesn't match
            (
                ("5.14-14", "generic", "arm64", "focal"),
                LivepatchSupportCacheData(
                    version="5.14-14",
                    flavor="generic",
                    arch="amd64",
                    codename="focal",
                    cached_at=datetime.datetime.now(datetime.timezone.utc)
                    - datetime.timedelta(days=6),
                    supported=True,
                ),
                (False, None),
            ),
            # invalid codename doesn't match
            (
                ("5.14-14", "generic", "amd64", "xenial"),
                LivepatchSupportCacheData(
                    version="5.14-14",
                    flavor="generic",
                    arch="amd64",
                    codename="focal",
                    cached_at=datetime.datetime.now(datetime.timezone.utc)
                    - datetime.timedelta(days=6),
                    supported=True,
                ),
                (False, None),
            ),
            # invalid too old
            (
                ("5.14-14", "generic", "amd64", "xenial"),
                LivepatchSupportCacheData(
                    version="5.14-14",
                    flavor="generic",
                    arch="amd64",
                    codename="focal",
                    cached_at=datetime.datetime.now(datetime.timezone.utc)
                    - datetime.timedelta(days=8),
                    supported=True,
                ),
                (False, None),
            ),
        ],
    )
    @mock.patch(M_PATH + "state_files.livepatch_support_cache.read")
    def test_on_supported_kernel_cache(
        self,
        m_cache_read,
        args,
        cache_contents,
        expected,
    ):
        m_cache_read.return_value = cache_contents
        assert _on_supported_kernel_cache(*args) == expected

    @pytest.mark.parametrize(
        [
            "args",
            "is_kernel_supported",
            "expected_cache_write_call_args",
            "expected",
        ],
        [
            (
                ("5.14-14", "generic", "amd64", "focal"),
                True,
                [
                    mock.call(
                        LivepatchSupportCacheData(
                            version="5.14-14",
                            flavor="generic",
                            arch="amd64",
                            codename="focal",
                            supported=True,
                            cached_at=mock.ANY,
                        )
                    )
                ],
                True,
            ),
            (
                ("5.14-14", "kvm", "arm64", "focal"),
                False,
                [
                    mock.call(
                        LivepatchSupportCacheData(
                            version="5.14-14",
                            flavor="kvm",
                            arch="arm64",
                            codename="focal",
                            supported=False,
                            cached_at=mock.ANY,
                        )
                    )
                ],
                False,
            ),
            (
                ("4.14-14", "kvm", "arm64", "xenial"),
                None,
                [
                    mock.call(
                        LivepatchSupportCacheData(
                            version="4.14-14",
                            flavor="kvm",
                            arch="arm64",
                            codename="xenial",
                            supported=None,
                            cached_at=mock.ANY,
                        )
                    )
                ],
                None,
            ),
        ],
    )
    @mock.patch(M_PATH + "state_files.livepatch_support_cache.write")
    @mock.patch(M_PATH + "UALivepatchClient.is_kernel_supported")
    def test_on_supported_kernel_api(
        self,
        m_is_kernel_supported,
        m_cache_write,
        args,
        is_kernel_supported,
        expected_cache_write_call_args,
        expected,
    ):
        m_is_kernel_supported.return_value = is_kernel_supported
        assert _on_supported_kernel_api(*args) == expected
        assert m_cache_write.call_args_list == expected_cache_write_call_args

    @pytest.mark.parametrize(
        [
            "cli_result",
            "get_kernel_info_result",
            "standardize_arch_name_result",
            "get_release_info_result",
            "cache_result",
            "api_result",
            "cache_call_args",
            "api_call_args",
            "expected",
        ],
        [
            # cli result supported
            (
                LivepatchSupport.SUPPORTED,
                None,
                None,
                None,
                None,
                None,
                [],
                [],
                LivepatchSupport.SUPPORTED,
            ),
            # cli result unsupported
            (
                LivepatchSupport.UNSUPPORTED,
                None,
                None,
                None,
                None,
                None,
                [],
                [],
                LivepatchSupport.UNSUPPORTED,
            ),
            # cli result upgrade-required
            (
                LivepatchSupport.KERNEL_UPGRADE_REQUIRED,
                None,
                None,
                None,
                None,
                None,
                [],
                [],
                LivepatchSupport.KERNEL_UPGRADE_REQUIRED,
            ),
            # cli result eol
            (
                LivepatchSupport.KERNEL_EOL,
                None,
                None,
                None,
                None,
                None,
                [],
                [],
                LivepatchSupport.KERNEL_EOL,
            ),
            # cli result definite unknown
            (
                LivepatchSupport.UNKNOWN,
                None,
                None,
                None,
                None,
                None,
                [],
                [],
                LivepatchSupport.UNKNOWN,
            ),
            # insufficient kernel info
            (
                None,
                system.KernelInfo(
                    uname_machine_arch="",
                    uname_release="",
                    proc_version_signature_version="",
                    build_date=None,
                    flavor=None,
                    major=5,
                    minor=6,
                    abi=7,
                    patch=None,
                ),
                None,
                None,
                None,
                None,
                [],
                [],
                LivepatchSupport.UNKNOWN,
            ),
            # cache result true
            (
                None,
                system.KernelInfo(
                    uname_machine_arch="",
                    uname_release="",
                    proc_version_signature_version="",
                    build_date=None,
                    flavor="generic",
                    major=5,
                    minor=6,
                    abi=7,
                    patch=None,
                ),
                "amd64",
                mock.MagicMock(series="xenial"),
                (True, True),
                None,
                [mock.call("5.6", "generic", "amd64", "xenial")],
                [],
                LivepatchSupport.SUPPORTED,
            ),
            # cache result false
            (
                None,
                system.KernelInfo(
                    uname_machine_arch="",
                    uname_release="",
                    proc_version_signature_version="",
                    build_date=None,
                    flavor="generic",
                    major=5,
                    minor=6,
                    abi=7,
                    patch=None,
                ),
                "amd64",
                mock.MagicMock(series="xenial"),
                (True, False),
                None,
                [mock.call("5.6", "generic", "amd64", "xenial")],
                [],
                LivepatchSupport.UNSUPPORTED,
            ),
            # cache result none
            (
                None,
                system.KernelInfo(
                    uname_machine_arch="",
                    uname_release="",
                    proc_version_signature_version="",
                    build_date=None,
                    flavor="generic",
                    major=5,
                    minor=6,
                    abi=7,
                    patch=None,
                ),
                "amd64",
                mock.MagicMock(series="xenial"),
                (True, None),
                None,
                [mock.call("5.6", "generic", "amd64", "xenial")],
                [],
                LivepatchSupport.UNKNOWN,
            ),
            # api result true
            (
                None,
                system.KernelInfo(
                    uname_machine_arch="",
                    uname_release="",
                    proc_version_signature_version="",
                    build_date=None,
                    flavor="generic",
                    major=5,
                    minor=6,
                    abi=7,
                    patch=None,
                ),
                "amd64",
                mock.MagicMock(series="xenial"),
                (False, None),
                True,
                [mock.call("5.6", "generic", "amd64", "xenial")],
                [mock.call("5.6", "generic", "amd64", "xenial")],
                LivepatchSupport.SUPPORTED,
            ),
        ],
    )
    @mock.patch(M_PATH + "_on_supported_kernel_api")
    @mock.patch(M_PATH + "_on_supported_kernel_cache")
    @mock.patch(M_PATH + "system.get_release_info")
    @mock.patch(M_PATH + "util.standardize_arch_name")
    @mock.patch(M_PATH + "system.get_kernel_info")
    @mock.patch(M_PATH + "_on_supported_kernel_cli")
    def test_on_supported_kernel(
        self,
        m_supported_cli,
        m_get_kernel_info,
        m_standardize_arch_name,
        m_get_release_info,
        m_supported_cache,
        m_supported_api,
        cli_result,
        get_kernel_info_result,
        standardize_arch_name_result,
        get_release_info_result,
        cache_result,
        api_result,
        cache_call_args,
        api_call_args,
        expected,
    ):
        m_supported_cli.return_value = cli_result
        m_get_kernel_info.return_value = get_kernel_info_result
        m_standardize_arch_name.return_value = standardize_arch_name_result
        m_get_release_info.return_value = get_release_info_result
        m_supported_cache.return_value = cache_result
        m_supported_api.return_value = api_result
        assert on_supported_kernel.__wrapped__() == expected
        assert m_supported_cache.call_args_list == cache_call_args
        assert m_supported_api.call_args_list == api_call_args


class TestConfigureLivepatchProxy:
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
    def test_configure_livepatch_proxy(
        self, m_subp, http_proxy, https_proxy, retry_sleeps, capsys, event
    ):
        configure_livepatch_proxy(http_proxy, https_proxy, retry_sleeps)
        expected_calls = []
        if http_proxy:
            expected_calls.append(
                mock.call(
                    [
                        LIVEPATCH_CMD,
                        "config",
                        "http-proxy={}".format(http_proxy),
                    ],
                    retry_sleeps=retry_sleeps,
                )
            )

        if https_proxy:
            expected_calls.append(
                mock.call(
                    [
                        LIVEPATCH_CMD,
                        "config",
                        "https-proxy={}".format(https_proxy),
                    ],
                    retry_sleeps=retry_sleeps,
                )
            )

        assert m_subp.call_args_list == expected_calls

        out, _ = capsys.readouterr()
        if http_proxy or https_proxy:
            assert out.strip() == messages.SETTING_SERVICE_PROXY.format(
                service=LivepatchEntitlement.title
            )

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
    @mock.patch("uaclient.system.subp")
    def test_get_config_option_value(
        self, m_util_subp, key, subp_return_value, expected_ret
    ):
        m_util_subp.return_value = subp_return_value
        ret = get_config_option_value(key)
        assert ret == expected_ret
        assert [
            mock.call([LIVEPATCH_CMD, "config"])
        ] == m_util_subp.call_args_list


class TestUnconfigureLivepatchProxy:
    @pytest.mark.parametrize(
        "livepatch_installed, protocol_type, retry_sleeps",
        (
            (True, "http", None),
            (True, "https", [1]),
            (True, "http", []),
            (False, "http", None),
        ),
    )
    @mock.patch("uaclient.system.which")
    @mock.patch("uaclient.system.subp")
    def test_unconfigure_livepatch_proxy(
        self, subp, which, livepatch_installed, protocol_type, retry_sleeps
    ):
        if livepatch_installed:
            which.return_value = LIVEPATCH_CMD
        else:
            which.return_value = None
        kwargs = {"protocol_type": protocol_type}
        if retry_sleeps is not None:
            kwargs["retry_sleeps"] = retry_sleeps
        assert None is unconfigure_livepatch_proxy(**kwargs)
        if livepatch_installed:
            expected_calls = [
                mock.call(
                    [LIVEPATCH_CMD, "config", protocol_type + "-proxy="],
                    retry_sleeps=retry_sleeps,
                )
            ]
        else:
            expected_calls = []
        assert expected_calls == subp.call_args_list
