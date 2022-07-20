"""Tests related to uaclient.entitlement.base module."""

import contextlib
import copy
import datetime
import io
import logging
from functools import partial
from types import MappingProxyType

import mock
import pytest

from uaclient import apt, exceptions, messages, system
from uaclient.entitlements.entitlement_status import (
    ApplicabilityStatus,
    ApplicationStatus,
    CanEnableFailureReason,
    ContractStatus,
    UserFacingStatus,
)
from uaclient.entitlements.livepatch import (
    LIVEPATCH_CMD,
    LivepatchEntitlement,
    UALivepatchClient,
    _on_supported_kernel_api,
    _on_supported_kernel_cache,
    _on_supported_kernel_cli,
    configure_livepatch_proxy,
    get_config_option_value,
    on_supported_kernel,
    process_config_directives,
    unconfigure_livepatch_proxy,
)
from uaclient.entitlements.tests.conftest import machine_token
from uaclient.files.state_files import LivepatchSupportCacheData
from uaclient.snap import SNAP_CMD

PLATFORM_INFO_SUPPORTED = MappingProxyType(
    {
        "arch": "x86_64",
        "kernel": "4.4.0-00-generic",
        "series": "xenial",
        "version": "16.04 LTS (Xenial Xerus)",
    }
)

M_PATH = "uaclient.entitlements.livepatch."  # mock path
M_LIVEPATCH_STATUS = M_PATH + "LivepatchEntitlement.application_status"
DISABLED_APP_STATUS = (ApplicationStatus.DISABLED, "")

M_BASE_PATH = "uaclient.entitlements.base.UAEntitlement."

DEFAULT_AFFORDANCES = {
    "architectures": ["x86_64"],
    "minKernelVersion": "4.4",
    "kernelFlavors": ["generic", "lowlatency"],
    "tier": "stable",
}


@pytest.fixture
def livepatch_entitlement_factory(entitlement_factory):
    directives = {"caCerts": "", "remoteServer": "https://alt.livepatch.com"}
    return partial(
        entitlement_factory,
        LivepatchEntitlement,
        affordances=DEFAULT_AFFORDANCES,
        directives=directives,
    )


@pytest.fixture
def entitlement(livepatch_entitlement_factory):
    return livepatch_entitlement_factory()


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
                "x86_64",
                "xenial",
                [
                    mock.call(
                        "/v1/api/kernels/supported",
                        headers=mock.ANY,
                        query_params={
                            "kernel-version": "1.23-4",
                            "flavour": "generic",
                            "architecture": "x86_64",
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
            "is_livepatch_installed",
            "subp_side_effect",
            "expected",
        ],
        [
            (False, None, None),
            (True, exceptions.ProcessExecutionError(mock.MagicMock()), None),
            (True, [("{}", None)], None),
            (True, [('{"Status": []}', None)], None),
            (True, [('{"Status": [{}]}', None)], None),
            (True, [('{"Status": [{"Livepatch": {}}]}', None)], None),
            (
                True,
                [
                    (
                        '{"Status": [{"Supported": "supported"}]}',  # noqa: E501
                        None,
                    )
                ],
                True,
            ),
            (
                True,
                [
                    (
                        '{"Status": [{"Supported": "unsupported"}]}',  # noqa: E501
                        None,
                    )
                ],
                False,
            ),
            (
                True,
                [
                    (
                        '{"Status": [{"Supported": "unknown"}]}',  # noqa: E501
                        None,
                    )
                ],
                None,
            ),
        ],
    )
    @mock.patch(M_PATH + "system.subp")
    @mock.patch(M_PATH + "is_livepatch_installed")
    def test_on_supported_kernel_cli(
        self,
        m_is_livepatch_installed,
        m_subp,
        is_livepatch_installed,
        subp_side_effect,
        expected,
    ):
        m_is_livepatch_installed.return_value = is_livepatch_installed
        m_subp.side_effect = subp_side_effect
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
                ("5.14-14", "generic", "x86_64", "focal"),
                LivepatchSupportCacheData(
                    version="5.14-14",
                    flavor="generic",
                    arch="x86_64",
                    codename="focal",
                    cached_at=datetime.datetime.now(datetime.timezone.utc)
                    - datetime.timedelta(days=6),
                    supported=True,
                ),
                (True, True),
            ),
            # valid false
            (
                ("5.14-14", "generic", "x86_64", "focal"),
                LivepatchSupportCacheData(
                    version="5.14-14",
                    flavor="generic",
                    arch="x86_64",
                    codename="focal",
                    cached_at=datetime.datetime.now(datetime.timezone.utc)
                    - datetime.timedelta(days=6),
                    supported=False,
                ),
                (True, False),
            ),
            # valid none
            (
                ("5.14-14", "generic", "x86_64", "focal"),
                LivepatchSupportCacheData(
                    version="5.14-14",
                    flavor="generic",
                    arch="x86_64",
                    codename="focal",
                    cached_at=datetime.datetime.now(datetime.timezone.utc)
                    - datetime.timedelta(days=6),
                    supported=None,
                ),
                (True, None),
            ),
            # invalid version doesn't match
            (
                ("5.14-13", "generic", "x86_64", "focal"),
                LivepatchSupportCacheData(
                    version="5.14-14",
                    flavor="generic",
                    arch="x86_64",
                    codename="focal",
                    cached_at=datetime.datetime.now(datetime.timezone.utc)
                    - datetime.timedelta(days=6),
                    supported=True,
                ),
                (False, None),
            ),
            # invalid flavor doesn't match
            (
                ("5.14-14", "kvm", "x86_64", "focal"),
                LivepatchSupportCacheData(
                    version="5.14-14",
                    flavor="generic",
                    arch="x86_64",
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
                    arch="x86_64",
                    codename="focal",
                    cached_at=datetime.datetime.now(datetime.timezone.utc)
                    - datetime.timedelta(days=6),
                    supported=True,
                ),
                (False, None),
            ),
            # invalid codename doesn't match
            (
                ("5.14-14", "generic", "x86_64", "xenial"),
                LivepatchSupportCacheData(
                    version="5.14-14",
                    flavor="generic",
                    arch="x86_64",
                    codename="focal",
                    cached_at=datetime.datetime.now(datetime.timezone.utc)
                    - datetime.timedelta(days=6),
                    supported=True,
                ),
                (False, None),
            ),
            # invalid too old
            (
                ("5.14-14", "generic", "x86_64", "xenial"),
                LivepatchSupportCacheData(
                    version="5.14-14",
                    flavor="generic",
                    arch="x86_64",
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
                ("5.14-14", "generic", "x86_64", "focal"),
                True,
                [
                    mock.call(
                        LivepatchSupportCacheData(
                            version="5.14-14",
                            flavor="generic",
                            arch="x86_64",
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
            "get_platform_info_result",
            "cache_result",
            "api_result",
            "cache_call_args",
            "api_call_args",
            "expected",
        ],
        [
            # cli result true
            (
                True,
                None,
                None,
                None,
                None,
                None,
                [],
                [],
                True,
            ),
            # cli result false
            (
                False,
                None,
                None,
                None,
                None,
                None,
                [],
                [],
                False,
            ),
            # insufficient kernel info
            (
                None,
                system.KernelInfo(
                    uname_release="",
                    proc_version_signature_version="",
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
                None,
            ),
            # cache result true
            (
                None,
                system.KernelInfo(
                    uname_release="",
                    proc_version_signature_version="",
                    flavor="generic",
                    major=5,
                    minor=6,
                    abi=7,
                    patch=None,
                ),
                "amd64",
                {"series": "xenial"},
                (True, True),
                None,
                [mock.call("5.6", "generic", "amd64", "xenial")],
                [],
                True,
            ),
            # cache result false
            (
                None,
                system.KernelInfo(
                    uname_release="",
                    proc_version_signature_version="",
                    flavor="generic",
                    major=5,
                    minor=6,
                    abi=7,
                    patch=None,
                ),
                "amd64",
                {"series": "xenial"},
                (True, False),
                None,
                [mock.call("5.6", "generic", "amd64", "xenial")],
                [],
                False,
            ),
            # cache result none
            (
                None,
                system.KernelInfo(
                    uname_release="",
                    proc_version_signature_version="",
                    flavor="generic",
                    major=5,
                    minor=6,
                    abi=7,
                    patch=None,
                ),
                "amd64",
                {"series": "xenial"},
                (True, None),
                None,
                [mock.call("5.6", "generic", "amd64", "xenial")],
                [],
                None,
            ),
            # api result true
            (
                None,
                system.KernelInfo(
                    uname_release="",
                    proc_version_signature_version="",
                    flavor="generic",
                    major=5,
                    minor=6,
                    abi=7,
                    patch=None,
                ),
                "amd64",
                {"series": "xenial"},
                (False, None),
                True,
                [mock.call("5.6", "generic", "amd64", "xenial")],
                [mock.call("5.6", "generic", "amd64", "xenial")],
                True,
            ),
        ],
    )
    @mock.patch(M_PATH + "_on_supported_kernel_api")
    @mock.patch(M_PATH + "_on_supported_kernel_cache")
    @mock.patch(M_PATH + "system.get_platform_info")
    @mock.patch(M_PATH + "util.standardize_arch_name")
    @mock.patch(M_PATH + "system.get_lscpu_arch")
    @mock.patch(M_PATH + "system.get_kernel_info")
    @mock.patch(M_PATH + "_on_supported_kernel_cli")
    def test_on_supported_kernel(
        self,
        m_supported_cli,
        m_get_kernel_info,
        m_get_lscpu_arch,
        m_standardize_arch_name,
        m_get_platform_info,
        m_supported_cache,
        m_supported_api,
        cli_result,
        get_kernel_info_result,
        standardize_arch_name_result,
        get_platform_info_result,
        cache_result,
        api_result,
        cache_call_args,
        api_call_args,
        expected,
    ):
        m_supported_cli.return_value = cli_result
        m_get_kernel_info.return_value = get_kernel_info_result
        m_standardize_arch_name.return_value = standardize_arch_name_result
        m_get_platform_info.return_value = get_platform_info_result
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


class TestLivepatchContractStatus:
    def test_contract_status_entitled(self, entitlement):
        """The contract_status returns ENTITLED when entitled is True."""
        assert ContractStatus.ENTITLED == entitlement.contract_status()

    def test_contract_status_unentitled(self, livepatch_entitlement_factory):
        """The contract_status returns NONE when entitled is False."""
        entitlement = livepatch_entitlement_factory(entitled=False)
        assert ContractStatus.UNENTITLED == entitlement.contract_status()


class TestLivepatchUserFacingStatus:
    @mock.patch(
        "uaclient.entitlements.livepatch.on_supported_kernel",
        return_value=None,
    )
    @mock.patch(
        "uaclient.entitlements.livepatch.system.is_container",
        return_value=True,
    )
    def test_user_facing_status_inapplicable_on_inapplicable_status(
        self,
        _m_is_container,
        _m_on_supported_kernel,
        livepatch_entitlement_factory,
    ):
        """The user-facing details INAPPLICABLE applicability_status"""
        affordances = copy.deepcopy(DEFAULT_AFFORDANCES)
        affordances["series"] = ["bionic"]

        entitlement = livepatch_entitlement_factory(affordances=affordances)

        with mock.patch(
            "uaclient.system.get_platform_info"
        ) as m_platform_info:
            m_platform_info.return_value = PLATFORM_INFO_SUPPORTED
            uf_status, details = entitlement.user_facing_status()
        assert uf_status == UserFacingStatus.INAPPLICABLE
        expected_details = "Cannot install Livepatch on a container."
        assert expected_details == details.msg

    def test_user_facing_status_unavailable_on_unentitled(self, entitlement):
        """Status UNAVAILABLE on absent entitlement contract status."""
        no_entitlements = machine_token(LivepatchEntitlement.name)
        # Delete livepatch entitlement info
        no_entitlements["machineTokenInfo"]["contractInfo"][
            "resourceEntitlements"
        ].pop()
        entitlement.cfg.machine_token_file.write(no_entitlements)

        with mock.patch(
            "uaclient.system.get_platform_info"
        ) as m_platform_info:
            m_platform_info.return_value = PLATFORM_INFO_SUPPORTED
            uf_status, details = entitlement.user_facing_status()
        assert uf_status == UserFacingStatus.UNAVAILABLE
        assert "Livepatch is not entitled" == details.msg


class TestLivepatchProcessConfigDirectives:
    @pytest.mark.parametrize(
        "directive_key,livepatch_param_tmpl",
        (("remoteServer", "remote-server={}"), ("caCerts", "ca-certs={}")),
    )
    def test_call_livepatch_config_command(
        self, directive_key, livepatch_param_tmpl
    ):
        """Livepatch config directives are passed to livepatch config."""
        directive_value = "{}-value".format(directive_key)
        cfg = {"entitlement": {"directives": {directive_key: directive_value}}}
        with mock.patch("uaclient.system.subp") as m_subp:
            process_config_directives(cfg)
        expected_subp = mock.call(
            [
                LIVEPATCH_CMD,
                "config",
                livepatch_param_tmpl.format(directive_value),
            ],
            capture=True,
        )
        assert [expected_subp] == m_subp.call_args_list

    def test_handle_multiple_directives(self):
        """Handle multiple Livepatch directives using livepatch config."""
        cfg = {
            "entitlement": {
                "directives": {
                    "remoteServer": "value1",
                    "caCerts": "value2",
                    "ignored": "ignoredvalue",
                }
            }
        }
        with mock.patch("uaclient.system.subp") as m_subp:
            process_config_directives(cfg)
        expected_calls = [
            mock.call(
                [LIVEPATCH_CMD, "config", "ca-certs=value2"], capture=True
            ),
            mock.call(
                [LIVEPATCH_CMD, "config", "remote-server=value1"], capture=True
            ),
        ]
        assert expected_calls == m_subp.call_args_list

    @pytest.mark.parametrize("directives", ({}, {"otherkey": "othervalue"}))
    def test_ignores_other_or_absent(self, directives):
        """Ignore empty or unexpected directives and do not call livepatch."""
        cfg = {"entitlement": {"directives": directives}}
        with mock.patch("uaclient.system.subp") as m_subp:
            process_config_directives(cfg)
        assert 0 == m_subp.call_count


@mock.patch(
    "uaclient.entitlements.fips.FIPSEntitlement.application_status",
    return_value=DISABLED_APP_STATUS,
)
@mock.patch(M_LIVEPATCH_STATUS, return_value=DISABLED_APP_STATUS)
@mock.patch(
    "uaclient.entitlements.livepatch.system.is_container", return_value=False
)
class TestLivepatchEntitlementCanEnable:
    @pytest.mark.parametrize(
        "supported_kernel_ver",
        (
            system.KernelInfo(
                uname_release="4.4.0-00-generic",
                proc_version_signature_version="",
                major=4,
                minor=4,
                patch=0,
                abi="00",
                flavor="generic",
            ),
            system.KernelInfo(
                uname_release="5.0.0-00-generic",
                proc_version_signature_version="",
                major=5,
                minor=0,
                patch=0,
                abi="00",
                flavor="generic",
            ),
            system.KernelInfo(
                uname_release="4.19.0-00-generic",
                proc_version_signature_version="",
                major=4,
                minor=19,
                patch=0,
                abi="00",
                flavor="generic",
            ),
        ),
    )
    @mock.patch("uaclient.system.get_kernel_info")
    @mock.patch(
        "uaclient.system.get_platform_info",
        return_value=PLATFORM_INFO_SUPPORTED,
    )
    def test_can_enable_true_on_entitlement_inactive(
        self,
        _m_platform,
        m_kernel_info,
        _m_is_container,
        _m_livepatch_status,
        _m_fips_status,
        supported_kernel_ver,
        capsys,
        entitlement,
    ):
        """When entitlement is INACTIVE, can_enable returns True."""
        m_kernel_info.return_value = supported_kernel_ver
        with mock.patch("uaclient.system.is_container") as m_container:
            m_container.return_value = False
            assert (True, None) == entitlement.can_enable()
        assert ("", "") == capsys.readouterr()
        assert [mock.call()] == m_container.call_args_list

    def test_can_enable_false_on_containers(
        self, m_is_container, _m_livepatch_status, _m_fips_status, entitlement
    ):
        """When is_container is True, can_enable returns False."""
        unsupported_min_kernel = copy.deepcopy(dict(PLATFORM_INFO_SUPPORTED))
        unsupported_min_kernel["kernel"] = "4.2.9-00-generic"
        with mock.patch("uaclient.system.get_platform_info") as m_platform:
            m_platform.return_value = unsupported_min_kernel
            m_is_container.return_value = True
            entitlement = LivepatchEntitlement(entitlement.cfg)
            result, reason = entitlement.can_enable()
            assert False is result
            assert CanEnableFailureReason.INAPPLICABLE == reason.reason
            msg = "Cannot install Livepatch on a container."
            assert msg == reason.message.msg


class TestLivepatchProcessContractDeltas:
    @mock.patch(M_PATH + "LivepatchEntitlement.setup_livepatch_config")
    def test_true_on_parent_process_deltas(
        self, m_setup_livepatch_config, entitlement
    ):
        """When parent's process_contract_deltas returns True do no setup."""
        assert entitlement.process_contract_deltas({}, {}, False)
        assert [] == m_setup_livepatch_config.call_args_list

    @mock.patch(M_PATH + "LivepatchEntitlement.setup_livepatch_config")
    @mock.patch(M_PATH + "LivepatchEntitlement.application_status")
    @mock.patch(M_PATH + "LivepatchEntitlement.applicability_status")
    def test_false_on_inactive_livepatch_service(
        self,
        m_applicability_status,
        m_application_status,
        m_setup_livepatch_config,
        entitlement,
    ):
        """When livepatch is INACTIVE return False and do no setup."""
        m_applicability_status.return_value = (
            ApplicabilityStatus.APPLICABLE,
            "",
        )
        m_application_status.return_value = (
            ApplicationStatus.DISABLED,
            "",
        )
        deltas = {"entitlement": {"directives": {"caCerts": "new"}}}
        assert not entitlement.process_contract_deltas({}, deltas, False)
        assert [] == m_setup_livepatch_config.call_args_list

    @pytest.mark.parametrize(
        "directives,process_directives,process_token",
        (
            ({"caCerts": "new"}, True, False),
            ({"remoteServer": "new"}, True, False),
            ({"unhandledKey": "new"}, False, False),
        ),
    )
    @mock.patch(M_PATH + "LivepatchEntitlement.setup_livepatch_config")
    @mock.patch(M_PATH + "LivepatchEntitlement.application_status")
    def test_setup_performed_when_active_and_supported_deltas(
        self,
        m_application_status,
        m_setup_livepatch_config,
        entitlement,
        directives,
        process_directives,
        process_token,
    ):
        """Run setup when livepatch ACTIVE and deltas are supported keys."""
        application_status = ApplicationStatus.ENABLED
        m_application_status.return_value = (application_status, "")
        deltas = {"entitlement": {"directives": directives}}
        assert entitlement.process_contract_deltas({}, deltas, False)
        if any([process_directives, process_token]):
            setup_calls = [
                mock.call(
                    process_directives=process_directives,
                    process_token=process_token,
                )
            ]
        else:
            setup_calls = []
        assert setup_calls == m_setup_livepatch_config.call_args_list

    @pytest.mark.parametrize(
        "deltas,process_directives,process_token",
        (
            ({"entitlement": {"something": 1}}, False, False),
            ({"resourceToken": "new"}, False, True),
        ),
    )
    @mock.patch(M_PATH + "LivepatchEntitlement.setup_livepatch_config")
    @mock.patch(M_PATH + "LivepatchEntitlement.application_status")
    def test_livepatch_disable_and_setup_performed_when_resource_token_changes(
        self,
        m_application_status,
        m_setup_livepatch_config,
        entitlement,
        deltas,
        process_directives,
        process_token,
    ):
        """Run livepatch calls setup when resourceToken changes."""
        application_status = ApplicationStatus.ENABLED
        m_application_status.return_value = (application_status, "")
        entitlement.process_contract_deltas({}, deltas, False)
        if any([process_directives, process_token]):
            setup_calls = [
                mock.call(
                    process_directives=process_directives,
                    process_token=process_token,
                )
            ]
        else:
            setup_calls = []
        assert setup_calls == m_setup_livepatch_config.call_args_list


@mock.patch(M_PATH + "snap.is_installed")
@mock.patch("uaclient.util.validate_proxy", side_effect=lambda x, y, z: y)
@mock.patch("uaclient.snap.configure_snap_proxy")
@mock.patch("uaclient.entitlements.livepatch.configure_livepatch_proxy")
class TestLivepatchEntitlementEnable:

    mocks_apt_update = [mock.call()]
    mocks_snapd_install = [
        mock.call(
            ["apt-get", "install", "--assume-yes", "snapd"],
            retry_sleeps=apt.APT_RETRIES,
        )
    ]
    mocks_snap_wait_seed = [
        mock.call(
            ["/usr/bin/snap", "wait", "system", "seed.loaded"], capture=True
        )
    ]
    mocks_livepatch_install = [
        mock.call(
            ["/usr/bin/snap", "install", "canonical-livepatch"],
            capture=True,
            retry_sleeps=[0.5, 1, 5],
        )
    ]
    mocks_install = (
        mocks_snapd_install + mocks_snap_wait_seed + mocks_livepatch_install
    )
    mocks_config = [
        mock.call(
            [
                LIVEPATCH_CMD,
                "config",
                "remote-server=https://alt.livepatch.com",
            ],
            capture=True,
        ),
        mock.call([LIVEPATCH_CMD, "disable"]),
        mock.call([LIVEPATCH_CMD, "enable", "livepatch-token"], capture=True),
    ]

    @pytest.mark.parametrize("caplog_text", [logging.DEBUG], indirect=True)
    @pytest.mark.parametrize("apt_update_success", (True, False))
    @mock.patch("uaclient.system.get_platform_info")
    @mock.patch("uaclient.system.subp")
    @mock.patch("uaclient.contract.apply_contract_overrides")
    @mock.patch("uaclient.apt.run_apt_install_command")
    @mock.patch("uaclient.apt.run_apt_update_command")
    @mock.patch("uaclient.system.which", return_value=None)
    @mock.patch(M_PATH + "LivepatchEntitlement.application_status")
    @mock.patch(
        M_PATH + "LivepatchEntitlement.can_enable", return_value=(True, None)
    )
    def test_enable_installs_snapd_and_livepatch_snap_when_absent(
        self,
        m_can_enable,
        m_app_status,
        m_which,
        m_run_apt_update,
        m_run_apt_install,
        _m_contract_overrides,
        m_subp,
        _m_get_platform_info,
        m_livepatch_proxy,
        m_snap_proxy,
        m_validate_proxy,
        m_is_installed,
        capsys,
        caplog_text,
        event,
        entitlement,
        apt_update_success,
    ):
        """Install snapd and canonical-livepatch snap when not on system."""
        application_status = ApplicationStatus.ENABLED
        m_app_status.return_value = application_status, "enabled"
        m_is_installed.return_value = False

        def fake_run_apt_update():
            if apt_update_success:
                return
            raise exceptions.UserFacingError("Apt go BOOM")

        m_run_apt_update.side_effect = fake_run_apt_update

        assert entitlement.enable()
        assert self.mocks_install + self.mocks_config in m_subp.call_args_list
        assert self.mocks_apt_update == m_run_apt_update.call_args_list
        msg = (
            "Installing snapd\n"
            "Updating package lists\n"
            "Installing canonical-livepatch snap\n"
            "Canonical livepatch enabled.\n"
        )
        assert (msg, "") == capsys.readouterr()
        expected_log = (
            "DEBUG    Trying to install snapd."
            " Ignoring apt-get update failure: Apt go BOOM"
        )
        if apt_update_success:
            assert expected_log not in caplog_text()
        else:
            assert expected_log in caplog_text()
        expected_calls = [mock.call("/usr/bin/snap"), mock.call(LIVEPATCH_CMD)]
        assert expected_calls == m_which.call_args_list
        assert m_validate_proxy.call_count == 2
        assert m_snap_proxy.call_count == 1
        assert m_livepatch_proxy.call_count == 1

    @mock.patch("uaclient.system.get_platform_info")
    @mock.patch("uaclient.system.subp")
    @mock.patch("uaclient.contract.apply_contract_overrides")
    @mock.patch(
        "uaclient.system.which",
        side_effect=lambda cmd: cmd if cmd == "/usr/bin/snap" else None,
    )
    @mock.patch(M_PATH + "LivepatchEntitlement.application_status")
    @mock.patch(
        M_PATH + "LivepatchEntitlement.can_enable", return_value=(True, None)
    )
    def test_enable_installs_only_livepatch_snap_when_absent_but_snapd_present(
        self,
        m_can_enable,
        m_app_status,
        m_which,
        _m_contract_overrides,
        m_subp,
        _m_get_platform_info,
        m_livepatch_proxy,
        m_snap_proxy,
        m_validate_proxy,
        m_is_installed,
        capsys,
        event,
        entitlement,
    ):
        """Install canonical-livepatch snap when not present on the system."""
        application_status = ApplicationStatus.ENABLED
        m_app_status.return_value = application_status, "enabled"
        m_is_installed.return_value = True

        assert entitlement.enable()
        assert (
            self.mocks_snap_wait_seed
            + self.mocks_livepatch_install
            + self.mocks_config
            in m_subp.call_args_list
        )
        msg = (
            "Installing canonical-livepatch snap\n"
            "Canonical livepatch enabled.\n"
        )
        assert (msg, "") == capsys.readouterr()
        expected_calls = [mock.call("/usr/bin/snap"), mock.call(LIVEPATCH_CMD)]
        assert expected_calls == m_which.call_args_list
        assert m_validate_proxy.call_count == 2
        assert m_snap_proxy.call_count == 1
        assert m_livepatch_proxy.call_count == 1

    @mock.patch("uaclient.system.subp")
    @mock.patch(
        "uaclient.system.which",
        side_effect=lambda cmd: cmd if cmd == "/usr/bin/snap" else None,
    )
    @mock.patch(M_PATH + "LivepatchEntitlement.application_status")
    @mock.patch(
        M_PATH + "LivepatchEntitlement.can_enable", return_value=(True, None)
    )
    def test_enable_fails_if_snap_cmd_exists_but_snapd_pkg_not_installed(
        self,
        m_can_enable,
        m_app_status,
        m_which,
        m_subp,
        m_livepatch_proxy,
        m_snap_proxy,
        m_validate_proxy,
        m_is_installed,
        capsys,
        entitlement,
    ):
        """Install canonical-livepatch snap when not present on the system."""
        m_app_status.return_value = ApplicationStatus.ENABLED, "enabled"
        m_is_installed.return_value = False

        with pytest.raises(exceptions.UserFacingError) as excinfo:
            entitlement.enable()

        expected_msg = (
            "/usr/bin/snap is present but snapd is not installed;"
            " cannot enable {}".format(entitlement.title)
        )
        assert expected_msg == excinfo.value.msg
        assert m_validate_proxy.call_count == 0
        assert m_snap_proxy.call_count == 0
        assert m_livepatch_proxy.call_count == 0

    @mock.patch("uaclient.system.get_platform_info")
    @mock.patch("uaclient.system.subp")
    @mock.patch("uaclient.contract.apply_contract_overrides")
    @mock.patch(
        "uaclient.system.which", side_effect=["/path/to/exe", "/path/to/exe"]
    )
    @mock.patch(M_PATH + "LivepatchEntitlement.application_status")
    @mock.patch(
        M_PATH + "LivepatchEntitlement.can_enable", return_value=(True, None)
    )
    def test_enable_does_not_install_livepatch_snap_when_present(
        self,
        m_can_enable,
        m_app_status,
        m_which,
        _m_contract_overrides,
        m_subp,
        _m_get_platform_info,
        m_livepatch_proxy,
        m_snap_proxy,
        m_validate_proxy,
        m_is_installed,
        capsys,
        event,
        entitlement,
    ):
        """Do not attempt to install livepatch snap when it is present."""
        application_status = ApplicationStatus.ENABLED
        m_app_status.return_value = application_status, "enabled"
        m_is_installed.return_value = True

        assert entitlement.enable()
        subp_calls = [
            mock.call(
                [SNAP_CMD, "wait", "system", "seed.loaded"], capture=True
            ),
            mock.call(
                [
                    LIVEPATCH_CMD,
                    "config",
                    "remote-server=https://alt.livepatch.com",
                ],
                capture=True,
            ),
            mock.call([LIVEPATCH_CMD, "disable"]),
            mock.call(
                [LIVEPATCH_CMD, "enable", "livepatch-token"], capture=True
            ),
        ]
        assert subp_calls == m_subp.call_args_list
        assert ("Canonical livepatch enabled.\n", "") == capsys.readouterr()
        assert m_validate_proxy.call_count == 2
        assert m_snap_proxy.call_count == 1
        assert m_livepatch_proxy.call_count == 1

    @mock.patch("uaclient.system.get_platform_info")
    @mock.patch("uaclient.system.subp")
    @mock.patch("uaclient.contract.apply_contract_overrides")
    @mock.patch(
        "uaclient.system.which", side_effect=["/path/to/exe", "/path/to/exe"]
    )
    @mock.patch(M_PATH + "LivepatchEntitlement.application_status")
    @mock.patch(
        M_PATH + "LivepatchEntitlement.can_enable", return_value=(True, None)
    )
    def test_enable_does_not_disable_inactive_livepatch_snap_when_present(
        self,
        m_can_enable,
        m_app_status,
        m_which,
        _m_contract_overrides,
        m_subp,
        _m_get_platform_info,
        m_livepatch_proxy,
        m_snap_proxy,
        m_validate_proxy,
        m_is_installed,
        capsys,
        entitlement,
    ):
        """Do not attempt to disable livepatch snap when it is inactive."""
        m_app_status.return_value = ApplicationStatus.DISABLED, "nope"
        m_is_installed.return_value = True

        assert entitlement.enable()
        subp_no_livepatch_disable = [
            mock.call(
                [SNAP_CMD, "wait", "system", "seed.loaded"], capture=True
            ),
            mock.call(
                [
                    LIVEPATCH_CMD,
                    "config",
                    "remote-server=https://alt.livepatch.com",
                ],
                capture=True,
            ),
            mock.call(
                [LIVEPATCH_CMD, "enable", "livepatch-token"], capture=True
            ),
        ]
        assert subp_no_livepatch_disable == m_subp.call_args_list
        assert ("Canonical livepatch enabled.\n", "") == capsys.readouterr()
        assert m_validate_proxy.call_count == 2
        assert m_snap_proxy.call_count == 1
        assert m_livepatch_proxy.call_count == 1

    @pytest.mark.parametrize(
        "cls_name, cls_title", (("FIPSEntitlement", "FIPS"),)
    )
    @mock.patch("uaclient.util.handle_message_operations")
    @mock.patch("uaclient.system.is_container", return_value=False)
    def test_enable_fails_when_blocking_service_is_enabled(
        self,
        m_is_container,
        m_handle_message_op,
        m_livepatch_proxy,
        m_snap_proxy,
        m_validate_proxy,
        _m_is_installed,
        cls_name,
        cls_title,
        entitlement,
    ):
        m_handle_message_op.return_value = True

        with mock.patch(M_LIVEPATCH_STATUS, return_value=DISABLED_APP_STATUS):
            with mock.patch(
                "uaclient.entitlements.fips.{}.application_status".format(
                    cls_name
                )
            ) as m_fips:
                m_fips.return_value = (ApplicationStatus.ENABLED, "")
                result, reason = entitlement.enable()
                assert not result

                msg = "Cannot enable Livepatch when {} is enabled.".format(
                    cls_title
                )
                assert msg.strip() == reason.message.msg.strip()

        assert m_validate_proxy.call_count == 0
        assert m_snap_proxy.call_count == 0
        assert m_livepatch_proxy.call_count == 0

    @pytest.mark.parametrize("caplog_text", [logging.WARN], indirect=True)
    @mock.patch("uaclient.system.which")
    @mock.patch("uaclient.system.subp")
    def test_enable_alerts_user_that_snapd_does_not_wait_command(
        self,
        m_subp,
        m_which,
        m_livepatch_proxy,
        m_snap_proxy,
        m_validate_proxy,
        m_is_installed,
        entitlement,
        capsys,
        caplog_text,
        event,
    ):
        m_which.side_effect = ["/path/to/exe", None]
        m_is_installed.return_value = True

        stderr_msg = (
            "error: Unknown command `wait'. Please specify one command of: "
            "abort, ack, buy, change, changes, connect, create-user, disable,"
            " disconnect, download, enable, find, help, install, interfaces, "
            "known, list, login, logout, refresh, remove, run or try"
        )

        m_subp.side_effect = [
            exceptions.ProcessExecutionError(
                cmd="snapd wait system seed.loaded",
                exit_code=-1,
                stdout="",
                stderr=stderr_msg,
            ),
            True,
        ]

        fake_stdout = io.StringIO()

        with mock.patch.object(entitlement, "can_enable") as m_can_enable:
            m_can_enable.return_value = (True, None)
            with mock.patch.object(
                entitlement, "setup_livepatch_config"
            ) as m_setup_livepatch:
                with contextlib.redirect_stdout(fake_stdout):
                    entitlement.enable()

                assert 1 == m_can_enable.call_count
                assert 1 == m_setup_livepatch.call_count

        assert (
            "Installing canonical-livepatch snap"
            in fake_stdout.getvalue().strip()
        )

        for msg in messages.SNAPD_DOES_NOT_HAVE_WAIT_CMD.split("\n"):
            assert msg in caplog_text()

        assert m_validate_proxy.call_count == 2
        assert m_snap_proxy.call_count == 1
        assert m_livepatch_proxy.call_count == 1

    @mock.patch("uaclient.entitlements.livepatch.apt.run_apt_update_command")
    @mock.patch("uaclient.system.which")
    @mock.patch("uaclient.system.subp")
    def test_enable_raise_exception_when_snapd_cant_be_installed(
        self,
        m_subp,
        m_which,
        _m_apt_update,
        m_livepatch_proxy,
        m_snap_proxy,
        m_validate_proxy,
        _m_is_installed,
        entitlement,
    ):
        m_which.side_effect = [False, True]

        m_subp.side_effect = exceptions.ProcessExecutionError(
            cmd="apt-get install --assume-yes snapd",
            exit_code=-1,
        )

        with mock.patch.object(entitlement, "can_enable") as m_can_enable:
            m_can_enable.return_value = (True, None)
            with mock.patch.object(
                entitlement, "setup_livepatch_config"
            ) as m_setup_livepatch:
                with pytest.raises(exceptions.CannotInstallSnapdError):
                    entitlement.enable()

            assert 1 == m_can_enable.call_count
            assert 0 == m_setup_livepatch.call_count

        assert m_validate_proxy.call_count == 0
        assert m_snap_proxy.call_count == 0
        assert m_livepatch_proxy.call_count == 0

    @mock.patch("uaclient.entitlements.livepatch.apt.run_apt_update_command")
    @mock.patch("uaclient.system.which")
    @mock.patch("uaclient.system.subp")
    def test_enable_raise_exception_for_unexpected_error_on_snapd_wait(
        self,
        m_subp,
        m_which,
        _m_apt_update,
        m_livepatch_proxy,
        m_snap_proxy,
        m_validate_proxy,
        m_is_installed,
        entitlement,
    ):
        m_which.side_effect = [None, "/path/to/exe"]
        m_is_installed.return_value = True
        stderr_msg = "test error"

        # No side effect when trying to install snapd,
        # Exception when trying to wait
        m_subp.side_effect = [
            None,
            exceptions.ProcessExecutionError(
                cmd="snapd wait system seed.loaded",
                exit_code=-1,
                stdout="",
                stderr=stderr_msg,
            ),
        ]

        with mock.patch.object(entitlement, "can_enable") as m_can_enable:
            m_can_enable.return_value = (True, None)
            with mock.patch.object(
                entitlement, "setup_livepatch_config"
            ) as m_setup_livepatch:
                with pytest.raises(
                    exceptions.ProcessExecutionError
                ) as excinfo:
                    entitlement.enable()

            assert 1 == m_can_enable.call_count
            assert 0 == m_setup_livepatch.call_count

        expected_msg = "test error"
        assert expected_msg in str(excinfo)
        assert m_validate_proxy.call_count == 0
        assert m_snap_proxy.call_count == 0
        assert m_livepatch_proxy.call_count == 0


class TestLivepatchApplicationStatus:
    @pytest.mark.parametrize("which_result", (("/path/to/exe"), (None)))
    @pytest.mark.parametrize("subp_raise_exception", ((True), (False)))
    @mock.patch("uaclient.system.which")
    @mock.patch("uaclient.system.subp")
    def test_application_status(
        self, m_subp, m_which, subp_raise_exception, which_result, entitlement
    ):
        m_which.return_value = which_result

        if subp_raise_exception:
            m_subp.side_effect = exceptions.ProcessExecutionError("error msg")

        status, details = entitlement.application_status()

        if not which_result:
            assert status == ApplicationStatus.DISABLED
            assert "canonical-livepatch snap is not installed." in details.msg
        elif subp_raise_exception:
            assert status == ApplicationStatus.DISABLED
            assert "error msg" in details.msg
        else:
            assert status == ApplicationStatus.ENABLED
            assert details is None

    @mock.patch("time.sleep")
    @mock.patch("uaclient.system.which", return_value="/path/to/exe")
    def test_status_command_retry_on_application_status(
        self, m_which, m_sleep, entitlement
    ):
        from uaclient import system

        with mock.patch.object(system, "_subp") as m_subp:
            m_subp.side_effect = exceptions.ProcessExecutionError("error msg")
            status, details = entitlement.application_status()

            assert m_subp.call_count == 3
            assert m_sleep.call_count == 2
            assert status == ApplicationStatus.DISABLED
            assert "error msg" in details.msg
