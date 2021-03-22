import copy
import mock
import os
import pytest
import textwrap

from uaclient.security import (
    API_V1_CVES,
    API_V1_CVE_TMPL,
    API_V1_NOTICES,
    API_V1_NOTICE_TMPL,
    CVE,
    CVEPackageStatus,
    UASecurityClient,
    USN,
    SecurityAPIError,
    fix_security_issue_id,
    get_cve_affected_source_packages_status,
    merge_usn_released_binary_package_versions,
    override_usn_release_package_status,
    prompt_for_affected_packages,
    query_installed_source_pkg_versions,
    upgrade_packages_and_attach,
    version_cmp_le,
)
from uaclient.status import (
    MESSAGE_SECURITY_USE_PRO_TMPL,
    OKGREEN_CHECK,
    FAIL_X,
    MESSAGE_SECURITY_APT_NON_ROOT,
    MESSAGE_SECURITY_UA_SERVICE_NOT_ENABLED,
    MESSAGE_SECURITY_UA_SERVICE_NOT_ENTITLED,
    MESSAGE_SECURITY_ISSUE_NOT_RESOLVED,
    MESSAGE_SECURITY_UPDATE_NOT_INSTALLED_SUBSCRIPTION as MSG_SUBSCRIPTION,
    MESSAGE_SECURITY_SERVICE_DISABLED,
    PROMPT_ENTER_TOKEN,
    UserFacingStatus,
    ApplicabilityStatus,
    colorize_commands,
)
from uaclient import exceptions
from uaclient.util import UrlError

M_PATH = "uaclient.contract."
M_REPO_PATH = "uaclient.entitlements.repo.RepoEntitlement."


SAMPLE_GET_CVES_QUERY_PARAMS = {
    "query": "vq",
    "priority": "vpr",
    "package": "vpa",
    "limit": 1,
    "offset": 2,
    "component": "vc",
    "version": "vv",
    "status": "vs",
}

SAMPLE_GET_NOTICES_QUERY_PARAMS = {
    "details": "vd",
    "release": "vq",
    "limit": 1,
    "offset": 2,
    "order": "vo",
}


CVE_ESM_PACKAGE_STATUS_RESPONSE = {
    "component": None,
    "description": "1.17-6ubuntu4.1+esm1",
    "pocket": "esm-infra",
    "release_codename": "focal",
    "status": "released",
}


SAMBA_CVE_STATUS_BIONIC = {
    "component": None,
    "description": "2:4.7.6+dfsg~ubuntu-0ubuntu2.19",
    "pocket": None,
    "release_codename": "bionic",
    "status": "released",
}
SAMBA_CVE_STATUS_FOCAL = {
    "component": None,
    "description": "2:4.11.6+dfsg-0ubuntu1.4",
    "pocket": None,
    "release_codename": "focal",
    "status": "not-affected",
}
SAMBA_CVE_STATUS_UPSTREAM = {
    "component": None,
    "description": "",
    "pocket": None,
    "release_codename": "upstream",
    "status": "needs-triage",
}

SAMPLE_CVE_RESPONSE = {
    "bugs": ["https://bugzilla.samba.org/show_bug.cgi?id=14497"],
    "description": "\nAn elevation of privilege vulnerability exists ...",
    "id": "CVE-2020-1472",
    "notes": [{"author": "..", "note": "..."}],
    "notices": ["USN-4510-1", "USN-4510-2", "USN-4559-1"],
    "packages": [
        {
            "debian": "https://tracker.debian.org/pkg/samba",
            "name": "samba",
            "source": "https://ubuntu.com/security/cve?package=samba",
            "statuses": [
                SAMBA_CVE_STATUS_BIONIC,
                SAMBA_CVE_STATUS_FOCAL,
                SAMBA_CVE_STATUS_UPSTREAM,
            ],
        }
    ],
    "status": "active",
}

SAMPLE_USN_RESPONSE = {
    "cves": ["CVE-2020-1473", "CVE-2020-1472"],
    "id": "USN-4510-2",
    "instructions": "In general, a standard system update will make all ...\n",
    "references": [],
    "release_packages": {
        "trusty": [
            {
                "description": "SMB/CIFS file, print, and login ... Unix",
                "is_source": True,
                "name": "samba",
                "version": "2:4.3.11+dfsg-0ubuntu0.14.04.20+esm9",
            },
            {
                "is_source": False,
                "name": "samba",
                "source_link": "https://launchpad.net/ubuntu/+source/samba",
                "version": "2~14.04.1+esm9",
                "version_link": "https://....11+dfsg-0ubuntu0.14.04.20+esm9",
            },
        ],
        "bionic": [
            {
                "description": "high-level 3D graphics kit implementing ...",
                "is_source": True,
                "name": "coin3",
                "version": "3.1.4~abc9f50-4ubuntu2+esm1",
            },
            {
                "is_source": False,
                "name": "libcoin80-runtime",
                "source_link": "https://launchpad.net/ubuntu/+source/coin3",
                "version": "3~18.04.1+esm2",
                "version_link": "https://coin3...18.04.1+esm2",
            },
        ],
    },
    "summary": "Samba would allow unintended access to files over the ....\n",
    "title": "Samba vulnerability",
    "type": "USN",
}


class TestGetCVEAffectedPackageStatus:
    @pytest.mark.parametrize(
        "series,installed_packages,expected_status",
        (
            ("bionic", {}, {}),
            # installed package version has no bearing on status filtering
            ("bionic", {"samba": "1000"}, SAMBA_CVE_STATUS_BIONIC),
            # active series has a bearing on status filtering
            ("upstream", {"samba": "1000"}, SAMBA_CVE_STATUS_UPSTREAM),
            # package status not-affected gets filtered from affected_pkgs
            ("focal", {"samba": "1000"}, {}),
        ),
    )
    @mock.patch("uaclient.security.util.get_platform_info")
    def test_affected_packages_status_filters_by_installed_pkgs_and_series(
        self,
        get_platform_info,
        series,
        installed_packages,
        expected_status,
        FakeConfig,
    ):
        """Package statuses are filtered if not installed"""
        get_platform_info.return_value = {"series": series}
        client = UASecurityClient(FakeConfig())
        cve = CVE(client, SAMPLE_CVE_RESPONSE)
        affected_packages = get_cve_affected_source_packages_status(
            cve, installed_packages=installed_packages
        )
        if expected_status:
            package_status = affected_packages["samba"]
            assert expected_status == package_status.response
        else:
            assert expected_status == affected_packages


class TestVersionCmpLe:
    @pytest.mark.parametrize(
        "ver1,ver2,is_lessorequal",
        (
            ("1.0", "2.0", True),
            ("2.0", "2.0", True),
            ("2.1~18.04.1", "2.1", True),
            ("2.1", "2.1~18.04.1", False),
            ("2.1", "2.0", False),
        ),
    )
    def test_version_cmp_le(self, ver1, ver2, is_lessorequal):
        """version_cmp_le returns True when ver1 less than or equal to ver2."""
        assert is_lessorequal is version_cmp_le(ver1, ver2)


class TestCVE:
    def test_cve_init_attributes(self, FakeConfig):
        """CVE.__init__ saves client and response on instance."""
        client = UASecurityClient(FakeConfig())
        cve = CVE(client, {"some": "response"})
        assert client == cve.client
        assert {"some": "response"} == cve.response

    @pytest.mark.parametrize(
        "attr_name,expected,response",
        (
            ("description", None, {}),
            ("description", "descr", {"description": "descr"}),
            ("id", "UNKNOWN_CVE_ID", {}),
            (
                "id",
                "CVE-123",
                {"id": "cve-123"},
            ),  # Uppercase of id value is used
            ("notice_ids", [], {}),
            ("notice_ids", [], {"notices": []}),
            ("notice_ids", ["1", "2"], {"notices": ["1", "2"]}),
        ),
    )
    def test_cve_basic_properties_from_response(
        self, attr_name, expected, response, FakeConfig
    ):
        """CVE instance properties are set from Security API CVE response."""
        client = UASecurityClient(FakeConfig())
        cve = CVE(client, response)
        assert expected == getattr(cve, attr_name)

    #  @mock.patch("uaclient.serviceclient.UAServiceClient.request_url")
    @mock.patch("uaclient.util.readurl")
    def test_get_url_header(self, request_url, FakeConfig):
        """CVE.get_url_header returns a string based on the CVE response."""
        client = UASecurityClient(FakeConfig())
        cve = CVE(client, SAMPLE_CVE_RESPONSE)
        request_url.return_value = (SAMPLE_USN_RESPONSE, "header")
        assert (
            textwrap.dedent(
                """\
                CVE-2020-1472: Samba vulnerability
                https://ubuntu.com/security/CVE-2020-1472"""
            )
            == cve.get_url_header()
        )
        headers = client.headers()
        calls = []
        for issue in ["USN-4559-1", "USN-4510-2", "USN-4510-1"]:
            calls.append(
                mock.call(
                    url="https://ubuntu.com/security/notices/{}.json".format(
                        issue
                    ),
                    data=None,
                    headers=headers,
                    method=None,
                    timeout=20,
                )
            )
        assert calls == request_url.call_args_list

    @mock.patch("uaclient.security.UASecurityClient.request_url")
    def test_get_notices_metadata(self, request_url, FakeConfig):
        """CVE.get_notices_metadata is cached to avoid extra round-trips."""
        client = UASecurityClient(FakeConfig())
        cve = CVE(client, SAMPLE_CVE_RESPONSE)

        def fake_request_url(url):
            usn = copy.deepcopy(SAMPLE_USN_RESPONSE)
            usn_id = os.path.basename(url).split(".")[0]
            usn["id"] = usn_id
            return (usn, "headers")

        request_url.side_effect = fake_request_url

        usns = cve.get_notices_metadata()
        assert ["USN-4559-1", "USN-4510-2", "USN-4510-1"] == [
            usn.id for usn in usns
        ]
        assert [
            mock.call("notices/USN-4559-1.json"),
            mock.call("notices/USN-4510-2.json"),
            mock.call("notices/USN-4510-1.json"),
        ] == request_url.call_args_list
        # no extra calls being made
        cve.get_notices_metadata()
        assert 3 == request_url.call_count


class TestUSN:
    def test_usn_init_attributes(self, FakeConfig):
        """USN.__init__ saves client and response on instance."""
        client = UASecurityClient(FakeConfig())
        cve = USN(client, {"some": "response"})
        assert client == cve.client
        assert {"some": "response"} == cve.response

    @pytest.mark.parametrize(
        "attr_name,expected,response",
        (
            ("title", None, {}),
            ("title", "my title", {"title": "my title"}),
            ("id", "UNKNOWN_USN_ID", {}),
            (
                "id",
                "USN-123",
                {"id": "usn-123"},
            ),  # Uppercase of id value is used
            ("cve_ids", [], {}),
            ("cve_ids", [], {"cves": []}),
            ("cve_ids", ["1", "2"], {"cves": ["1", "2"]}),
        ),
    )
    def test_usn_basic_properties_from_response(
        self, attr_name, expected, response, FakeConfig
    ):
        """USN instance properties are set from Security API USN response."""
        client = UASecurityClient(FakeConfig())
        usn = USN(client, response)
        assert expected == getattr(usn, attr_name)

    @pytest.mark.parametrize(
        "series,expected",
        (
            (
                "trusty",
                {
                    "samba": {
                        "source": {
                            "description": (
                                "SMB/CIFS file, print, and login ... Unix"
                            ),
                            "is_source": True,
                            "name": "samba",
                            "version": "2:4.3.11+dfsg-0ubuntu0.14.04.20+esm9",
                        },
                        "samba": {
                            "is_source": False,
                            "name": "samba",
                            "source_link": (
                                "https://launchpad.net/ubuntu/+source/samba"
                            ),
                            "version": "2~14.04.1+esm9",
                            "version_link": (
                                "https://....11+dfsg-0ubuntu0.14.04.20+esm9"
                            ),
                        },
                    }
                },
            ),
            (
                "bionic",
                {
                    "coin3": {
                        "source": {
                            "description": (
                                "high-level 3D graphics kit implementing ..."
                            ),
                            "is_source": True,
                            "name": "coin3",
                            "version": "3.1.4~abc9f50-4ubuntu2+esm1",
                        },
                        "libcoin80-runtime": {
                            "is_source": False,
                            "name": "libcoin80-runtime",
                            "source_link": (
                                "https://launchpad.net/ubuntu/+source/coin3"
                            ),
                            "version": "3~18.04.1+esm2",
                            "version_link": "https://coin3...18.04.1+esm2",
                        },
                    }
                },
            ),
            ("focal", {}),
        ),
    )
    @mock.patch("uaclient.util.get_platform_info")
    def test_release_packages_returns_source_and_binary_pkgs_for_series(
        self, get_platform_info, series, expected, FakeConfig
    ):
        get_platform_info.return_value = {"series": series}
        client = UASecurityClient(FakeConfig())
        usn = USN(client, SAMPLE_USN_RESPONSE)

        assert expected == usn.release_packages
        usn._release_packages = {"sl": "1.0"}
        assert {"sl": "1.0"} == usn.release_packages

    @pytest.mark.parametrize(
        "source_link,error_msg",
        (
            (
                None,
                "USN-4510-2 metadata does not define release_packages"
                " source_link for samba2.",
            ),
            (
                "unknown format",
                "USN-4510-2 metadata has unexpected release_packages"
                " source_link value for samba2: unknown format",
            ),
        ),
    )
    @mock.patch("uaclient.util.get_platform_info")
    def test_release_packages_errors_on_sparse_source_url(
        self, get_platform_info, source_link, error_msg, FakeConfig
    ):
        """Raise errors when USN metadata contains no valid source_link."""
        get_platform_info.return_value = {"series": "trusty"}
        client = UASecurityClient(FakeConfig())
        sparse_md = copy.deepcopy(SAMPLE_USN_RESPONSE)
        sparse_md["release_packages"]["trusty"].append(
            {
                "is_source": False,
                "name": "samba2",
                "source_link": source_link,
                "version": "2~14.04.1+esm9",
                "version_link": "https://....11+dfsg-0ubuntu0.14.04.20+esm9",
            }
        )
        usn = USN(client, sparse_md)
        with pytest.raises(exceptions.SecurityAPIMetadataError) as exc:
            usn.release_packages
        assert error_msg == str(exc.value)

    @mock.patch("uaclient.security.UASecurityClient.request_url")
    def test_get_cves_metadata(self, request_url, FakeConfig):
        """USN.get_cves_metadata is cached to avoid API round-trips."""
        client = UASecurityClient(FakeConfig())
        usn = USN(client, SAMPLE_USN_RESPONSE)

        def fake_request_url(url):
            cve = copy.deepcopy(SAMPLE_CVE_RESPONSE)
            cve_id = os.path.basename(url).split(".")[0]
            cve["id"] = cve_id
            return (cve, "headers")

        request_url.side_effect = fake_request_url

        cves = usn.get_cves_metadata()
        assert ["CVE-2020-1473", "CVE-2020-1472"] == [cve.id for cve in cves]
        assert [
            mock.call("cves/CVE-2020-1473.json"),
            mock.call("cves/CVE-2020-1472.json"),
        ] == request_url.call_args_list
        # no extra calls being made
        usn.get_cves_metadata()
        assert 2 == request_url.call_count

    def test_get_url_header(self, FakeConfig):
        """USN.get_url_header returns a string based on the USN response."""
        client = UASecurityClient(FakeConfig())
        usn = USN(client, SAMPLE_USN_RESPONSE)
        assert (
            textwrap.dedent(
                """\
                USN-4510-2: Samba vulnerability
                Found CVEs: CVE-2020-1473, CVE-2020-1472
                https://ubuntu.com/security/CVE-2020-1473
                https://ubuntu.com/security/CVE-2020-1472"""
            )
            == usn.get_url_header()
        )


class TestCVEPackageStatus:
    def test_simple_properties_from_response(self):
        pkg_status = CVEPackageStatus(
            cve_response=CVE_ESM_PACKAGE_STATUS_RESPONSE
        )
        assert CVE_ESM_PACKAGE_STATUS_RESPONSE == pkg_status.response
        assert pkg_status.response["description"] == pkg_status.description
        assert pkg_status.description == pkg_status.fixed_version
        assert pkg_status.response["pocket"] == pkg_status.pocket
        assert (
            pkg_status.response["release_codename"]
            == pkg_status.release_codename
        )
        assert pkg_status.response["status"] == pkg_status.status

    @pytest.mark.parametrize(
        "pocket,description,expected",
        (
            ("esm-infra", "1.2", "UA Infra"),
            ("esm-apps", "1.2", "UA Apps"),
            ("updates", "1.2esm", "Ubuntu standard updates"),
            ("security", "1.2esm", "Ubuntu standard updates"),
            (None, "1.2", "Ubuntu standard updates"),
            (None, "1.2esm", "UA Infra"),
        ),
    )
    def test_pocket_source_from_response(self, pocket, description, expected):
        cve_response = {"pocket": pocket, "description": description}
        pkg_status = CVEPackageStatus(cve_response=cve_response)
        assert expected == pkg_status.pocket_source

    @pytest.mark.parametrize(
        "pocket,description,expected",
        (
            ("esm-infra", "1.2", True),
            ("esm-apps", "1.2", True),
            ("updates", "1.2esm", False),
            ("security", "1.2esm", False),
            (None, "1.2", False),
            (None, "1.2esm", True),
        ),
    )
    def test_requires_ua_from_response(self, pocket, description, expected):
        """requires_ua is derived from response pocket and description."""
        cve_response = {"pocket": pocket, "description": description}
        pkg_status = CVEPackageStatus(cve_response=cve_response)
        assert expected is pkg_status.requires_ua

    @pytest.mark.parametrize(
        "status,pocket,expected",
        (
            (
                "not-affected",
                "",
                "Source package is not affected on this release.",
            ),
            ("DNE", "", "Source package does not exist on this release."),
            (
                "needs-triage",
                "esm-infra",
                "Ubuntu security engineers are investigating this issue.",
            ),
            ("needed", "esm-infra", "Sorry, no fix is available yet."),
            (
                "pending",
                "esm-infra",
                "A fix is coming soon. Try again tomorrow.",
            ),
            ("ignored", "esm-infra", "Sorry, no fix is available."),
            ("released", "esm-infra", "A fix is available in UA Infra."),
            (
                "released",
                "security",
                "A fix is available in Ubuntu standard updates.",
            ),
            ("bogus", "1.2", "UNKNOWN: bogus"),
        ),
    )
    def test_status_message_from_response(self, status, pocket, expected):
        cve_response = {"pocket": pocket, "status": status}
        pkg_status = CVEPackageStatus(cve_response=cve_response)
        assert expected == pkg_status.status_message


@mock.patch("uaclient.security.UASecurityClient.request_url")
class TestUASecurityClient:
    @pytest.mark.parametrize(
        "m_kwargs,expected_error, extra_security_params",
        (
            ({}, None, None),
            ({"query": "vq"}, None, {"test": "blah"}),
            (SAMPLE_GET_CVES_QUERY_PARAMS, None, None),
            ({"invalidparam": "vv"}, TypeError, None),
        ),
    )
    def test_get_cves_sets_query_params_on_get_cves_route(
        self,
        request_url,
        m_kwargs,
        expected_error,
        extra_security_params,
        FakeConfig,
    ):
        """GET CVE instances from API_V1_CVES route with querystrings"""
        cfg = FakeConfig()
        if extra_security_params:
            cfg.override_features(
                {"extra_security_params": extra_security_params}
            )

        client = UASecurityClient(cfg)
        if expected_error:
            with pytest.raises(expected_error) as exc:
                client.get_cves(**m_kwargs)
            assert (
                "get_cves() got an unexpected keyword argument 'invalidparam'"
            ) == str(exc.value)
            assert 0 == request_url.call_count
        else:
            for key in SAMPLE_GET_CVES_QUERY_PARAMS:
                if key not in m_kwargs:
                    m_kwargs[key] = None
            request_url.return_value = (["body1", "body2"], "headers")
            [cve1, cve2] = client.get_cves(**m_kwargs)
            assert isinstance(cve1, CVE)
            assert isinstance(cve2, CVE)
            assert "body1" == cve1.response
            assert "body2" == cve2.response
            # get_cves transposes "query" to "q"
            m_kwargs["q"] = m_kwargs.pop("query")

            assert [
                mock.call(API_V1_CVES, query_params=m_kwargs)
            ] == request_url.call_args_list

    @pytest.mark.parametrize(
        "m_kwargs,expected_error, extra_security_params",
        (
            ({}, None, None),
            ({"details": "vd"}, None, None),
            (SAMPLE_GET_NOTICES_QUERY_PARAMS, None, {"test": "blah"}),
            ({"invalidparam": "vv"}, TypeError, None),
        ),
    )
    def test_get_notices_sets_query_params_on_get_cves_route(
        self,
        request_url,
        m_kwargs,
        expected_error,
        extra_security_params,
        FakeConfig,
    ):
        """GET body from API_V1_NOTICES route with appropriate querystring"""
        cfg = FakeConfig()
        if extra_security_params:
            cfg.override_features(
                {"extra_security_params": extra_security_params}
            )

        client = UASecurityClient(cfg)
        if expected_error:
            with pytest.raises(expected_error) as exc:
                client.get_notices(**m_kwargs)
            assert (
                "get_notices() got an unexpected keyword argument"
                " 'invalidparam'"
            ) == str(exc.value)
            assert 0 == request_url.call_count
        else:
            for key in SAMPLE_GET_NOTICES_QUERY_PARAMS:
                if key not in m_kwargs:
                    m_kwargs[key] = None
            request_url.return_value = (
                {"notices": [{"id": "2"}, {"id": "1"}]},
                "headers",
            )
            [usn1, usn2] = client.get_notices(**m_kwargs)
            assert isinstance(usn1, USN)
            assert isinstance(usn2, USN)
            assert "1" == usn1.id
            assert "2" == usn2.id
            assert [
                mock.call(API_V1_NOTICES, query_params=m_kwargs)
            ] == request_url.call_args_list

    @pytest.mark.parametrize(
        "m_kwargs,expected_error, extra_security_params",
        (({}, TypeError, None), ({"cve_id": "CVE-1"}, None, {"test": "blah"})),
    )
    def test_get_cve_provides_response_from_cve_json_route(
        self,
        request_url,
        m_kwargs,
        expected_error,
        extra_security_params,
        FakeConfig,
    ):
        """GET body from API_V1_CVE_TMPL route with required cve_id."""
        cfg = FakeConfig()
        if extra_security_params:
            cfg.override_features(
                {"extra_security_params": extra_security_params}
            )
        client = UASecurityClient(cfg)
        if expected_error:
            with pytest.raises(expected_error) as exc:
                client.get_cve(**m_kwargs)
            assert (
                "get_cve() missing 1 required positional argument: 'cve_id'"
            ) == str(exc.value)
            assert 0 == request_url.call_count
        else:
            request_url.return_value = ("body", "headers")
            cve = client.get_cve(**m_kwargs)
            assert isinstance(cve, CVE)
            assert "body" == cve.response
            assert [
                mock.call(API_V1_CVE_TMPL.format(cve=m_kwargs["cve_id"]))
            ] == request_url.call_args_list

    @pytest.mark.parametrize(
        "m_kwargs,expected_error, extra_security_params",
        (
            ({}, TypeError, None),
            ({"notice_id": "USN-1"}, None, {"test": "blah"}),
        ),
    )
    def test_get_notice_provides_response_from_notice_json_route(
        self,
        request_url,
        m_kwargs,
        expected_error,
        extra_security_params,
        FakeConfig,
    ):
        """GET body from API_V1_NOTICE_TMPL route with required notice_id."""
        cfg = FakeConfig()
        if extra_security_params:
            cfg.override_features(
                {"extra_security_params": extra_security_params}
            )

        client = UASecurityClient(cfg)
        if expected_error:
            with pytest.raises(expected_error) as exc:
                client.get_notice(**m_kwargs)
            assert (
                "get_notice() missing 1 required positional argument:"
                " 'notice_id'"
            ) == str(exc.value)
            assert 0 == request_url.call_count
        else:
            request_url.return_value = ("body", "headers")
            assert "body" == client.get_notice(**m_kwargs).response
            assert [
                mock.call(
                    API_V1_NOTICE_TMPL.format(notice=m_kwargs["notice_id"])
                )
            ] == request_url.call_args_list


class TestQueryInstalledPkgSources:
    @pytest.mark.parametrize(
        "dpkg_out,results",
        (
            # Ignore b non-installed status
            ("a,,1.2,installed\nb,b,1.2,config-files", {"a": {"a": "1.2"}}),
            # Handle cases where no Source is defined for the pkg
            (
                "a,,1.2,installed\nzip,zip,3.0,installed",
                {"a": {"a": "1.2"}, "zip": {"zip": "3.0"}},
            ),
            # Prefer Source package name to binary package name
            (
                "b,bsrc,1.2,installed\nzip,zip,3.0,installed",
                {"bsrc": {"b": "1.2"}, "zip": {"zip": "3.0"}},
            ),
        ),
    )
    @pytest.mark.parametrize("series", ("trusty", "bionic"))
    @mock.patch("uaclient.security.util.subp")
    @mock.patch("uaclient.util.get_platform_info")
    def test_result_keyed_by_source_package_name(
        self, get_platform_info, subp, series, dpkg_out, results
    ):
        get_platform_info.return_value = {"series": series}
        subp.return_value = dpkg_out, ""
        assert results == query_installed_source_pkg_versions()
        if series == "trusty":
            _format = "-f=${Package},${Source},${Version},${Status}\n"
        else:
            _format = (
                "-f=${Package},${Source},${Version},${db:Status-Status}\n"
            )
        assert [
            mock.call(["dpkg-query", _format, "-W"])
        ] == subp.call_args_list


CVE_PKG_STATUS_NEEDED = {
    "description": "2.1",
    "pocket": None,
    "status": "needed",
}
CVE_PKG_STATUS_IGNORED = {
    "description": "2.1",
    "pocket": None,
    "status": "ignored",
}
CVE_PKG_STATUS_DEFERRED = {
    "description": "2.1",
    "pocket": None,
    "status": "deferred",
}
CVE_PKG_STATUS_NEEDS_TRIAGE = {
    "description": "2.1",
    "pocket": None,
    "status": "needs-triage",
}
CVE_PKG_STATUS_PENDING = {
    "description": "2.1",
    "pocket": None,
    "status": "pending",
}
CVE_PKG_STATUS_RELEASED = {
    "description": "2.1",
    "pocket": "updates",
    "status": "released",
}
CVE_PKG_STATUS_RELEASED_ESM_INFRA = {
    "description": "2.1",
    "pocket": "esm-infra",
    "status": "released",
}
CVE_PKG_STATUS_RELEASED_ESM_APPS = {
    "description": "2.1",
    "pocket": "esm-apps",
    "status": "released",
}
CVE_PKG_STATUS_NEEDED = {"description": "", "pocket": None, "status": "needed"}


class TestPromptForAffectedPackages:
    @pytest.mark.parametrize(
        "affected_pkg_status,installed_packages,usn_released_pkgs",
        (
            (
                {"slsrc": CVEPackageStatus(CVE_PKG_STATUS_RELEASED)},
                {"slsrc": {"sl": "2.0"}},
                {},
            ),
        ),
    )
    def test_raise_userfacing_error_on_invalid_usn_metadata(
        self,
        affected_pkg_status,
        installed_packages,
        usn_released_pkgs,
        FakeConfig,
    ):
        with pytest.raises(exceptions.SecurityAPIMetadataError) as exc:
            prompt_for_affected_packages(
                cfg=FakeConfig(),
                issue_id="USN-###",
                affected_pkg_status=affected_pkg_status,
                installed_packages=installed_packages,
                usn_released_pkgs=usn_released_pkgs,
            )
        assert (
            "Error: USN-### metadata defines no fixed version for sl.\n"
            "{msg}".format(
                msg=MESSAGE_SECURITY_ISSUE_NOT_RESOLVED.format(issue="USN-###")
            )
            == exc.value.msg
        )

    @pytest.mark.parametrize(
        "affected_pkg_status,installed_packages,"
        "usn_released_pkgs,cloud_type,expected",
        (
            (  # No affected_packages listed
                {},
                {"curl": {"curl": "1.0"}},
                {"unread-because-no-affected-pkgs": {}},
                None,
                textwrap.dedent(
                    """\
                    No affected packages are installed.
                    {check} USN-### does not affect your system.
                    """.format(
                        check=OKGREEN_CHECK  # noqa: E126
                    )  # noqa: E126
                ),
            ),
            (  # version is >= released affected package
                {"slsrc": CVEPackageStatus(CVE_PKG_STATUS_RELEASED)},
                {"slsrc": {"sl": "2.1"}},
                {"slsrc": {"sl": {"version": "2.1"}}},
                None,
                textwrap.dedent(
                    """\
                    1 affected package is installed: slsrc
                    (1/1) slsrc:
                    A fix is available in Ubuntu standard updates.
                    The update is already installed.
                    {check} USN-### is resolved.
                    """.format(
                        check=OKGREEN_CHECK  # noqa: E126
                    )  # noqa: E126
                ),
            ),
            (  # usn_released_pkgs version is used instead of CVE (2.1)
                {"slsrc": CVEPackageStatus(CVE_PKG_STATUS_RELEASED)},
                {"slsrc": {"sl": "2.1"}},
                {"slsrc": {"sl": {"version": "2.2"}}},
                None,
                textwrap.dedent(
                    """\
                    1 affected package is installed: slsrc
                    (1/1) slsrc:
                    A fix is available in Ubuntu standard updates.
                    """
                )
                + colorize_commands(
                    [["apt update && apt install --only-upgrade" " -y sl"]]
                )
                + "\n"
                + "{check} USN-### is resolved.\n".format(check=OKGREEN_CHECK),
            ),
            (  # version is < released affected package standard updates
                {"slsrc": CVEPackageStatus(CVE_PKG_STATUS_RELEASED)},
                {"slsrc": {"sl": "2.0"}},
                {"slsrc": {"sl": {"version": "2.1"}}},
                None,
                textwrap.dedent(
                    """\
                    1 affected package is installed: slsrc
                    (1/1) slsrc:
                    A fix is available in Ubuntu standard updates.
                    """
                )
                + "\n".join(
                    [
                        colorize_commands(
                            [
                                [
                                    "apt update && apt install --only-upgrade"
                                    " -y sl"
                                ]
                            ]
                        ),
                        "{check} USN-### is resolved.\n".format(
                            check=OKGREEN_CHECK
                        ),
                    ]
                ),
            ),
            (  # version is < released affected package esm-infra updates
                {"slsrc": CVEPackageStatus(CVE_PKG_STATUS_RELEASED_ESM_INFRA)},
                {"slsrc": {"sl": "2.0"}},
                {"slsrc": {"sl": {"version": "2.1"}}},
                "azure",
                textwrap.dedent(
                    """\
                    1 affected package is installed: slsrc
                    (1/1) slsrc:
                    A fix is available in UA Infra.
                    """
                )
                + "\n".join(
                    [
                        MESSAGE_SECURITY_USE_PRO_TMPL.format(
                            title="Azure", cloud="azure"
                        ),
                        MSG_SUBSCRIPTION,
                    ]
                ),
            ),
            (  # version < released package in esm-infra updates and aws cloud
                {"slsrc": CVEPackageStatus(CVE_PKG_STATUS_RELEASED_ESM_INFRA)},
                {"slsrc": {"sl": "2.0"}},
                {"slsrc": {"sl": {"version": "2.1"}}},
                "aws",
                textwrap.dedent(
                    """\
                    1 affected package is installed: slsrc
                    (1/1) slsrc:
                    A fix is available in UA Infra.
                    """
                )
                + "\n".join(
                    [
                        MESSAGE_SECURITY_USE_PRO_TMPL.format(
                            title="AWS", cloud="aws"
                        ),
                        MSG_SUBSCRIPTION,
                    ]
                ),
            ),
            (  # version is < released affected both esm-apps and standard
                {
                    "slsrc": CVEPackageStatus(
                        CVE_PKG_STATUS_RELEASED_ESM_APPS
                    ),
                    "curl": CVEPackageStatus(CVE_PKG_STATUS_RELEASED),
                },
                {"slsrc": {"sl": "2.0"}, "curl": {"curl": "2.0"}},
                {
                    "slsrc": {"sl": {"version": "2.1"}},
                    "curl": {"curl": {"version": "2.1"}},
                },
                "gcp",
                textwrap.dedent(
                    """\
                    2 affected packages are installed: curl, slsrc
                    (1/2) curl:
                    A fix is available in Ubuntu standard updates.
                    """
                )
                + colorize_commands(
                    [["apt update && apt install --only-upgrade" " -y curl"]]
                )
                + "\n"
                + textwrap.dedent(
                    """\
                    (2/2) slsrc:
                    A fix is available in UA Apps.
                    """
                )
                + MSG_SUBSCRIPTION,
            ),
            (  # version is < released affected both esm-apps and standard
                {
                    "pkg1": CVEPackageStatus(CVE_PKG_STATUS_IGNORED),
                    "pkg2": CVEPackageStatus(CVE_PKG_STATUS_IGNORED),
                    "pkg3": CVEPackageStatus(CVE_PKG_STATUS_PENDING),
                    "pkg4": CVEPackageStatus(CVE_PKG_STATUS_PENDING),
                    "pkg5": CVEPackageStatus(CVE_PKG_STATUS_NEEDS_TRIAGE),
                    "pkg6": CVEPackageStatus(CVE_PKG_STATUS_NEEDS_TRIAGE),
                    "pkg7": CVEPackageStatus(CVE_PKG_STATUS_NEEDED),
                    "pkg8": CVEPackageStatus(CVE_PKG_STATUS_NEEDED),
                    "pkg9": CVEPackageStatus(CVE_PKG_STATUS_DEFERRED),
                    "pkg10": CVEPackageStatus(CVE_PKG_STATUS_RELEASED),
                    "pkg11": CVEPackageStatus(CVE_PKG_STATUS_RELEASED),
                    "pkg12": CVEPackageStatus(
                        CVE_PKG_STATUS_RELEASED_ESM_INFRA
                    ),
                    "pkg13": CVEPackageStatus(
                        CVE_PKG_STATUS_RELEASED_ESM_INFRA
                    ),
                },
                {
                    "pkg10": {"pkg10": "2.0"},
                    "pkg11": {"pkg11": "2.0"},
                    "pkg12": {"pkg12": "2.0"},
                    "pkg13": {"pkg13": "2.0"},
                },
                {
                    "pkg10": {"pkg10": {"version": "2.1"}},
                    "pkg11": {"pkg11": {"version": "2.1"}},
                    "pkg12": {"pkg12": {"version": "2.1"}},
                    "pkg13": {"pkg13": {"version": "2.1"}},
                },
                "gcp",
                textwrap.dedent(
                    """\
                    13 affected packages are installed: {}
                    (1/13, 2/13, 3/13) pkg1, pkg2, pkg9:
                    Sorry, no fix is available.
                    (4/13, 5/13) pkg7, pkg8:
                    Sorry, no fix is available yet.
                    (6/13, 7/13) pkg5, pkg6:
                    Ubuntu security engineers are investigating this issue.
                    (8/13, 9/13) pkg3, pkg4:
                    A fix is coming soon. Try again tomorrow.
                    (10/13, 11/13) pkg10, pkg11:
                    A fix is available in Ubuntu standard updates.
                    """
                ).format(
                    (
                        "pkg1, pkg10, pkg11, pkg12, pkg13, pkg2, pkg3, pkg4,"
                        " pkg5, pkg6, pkg7, pkg8, pkg9"
                    )
                )
                + colorize_commands(
                    [
                        [
                            "apt update && apt install --only-upgrade"
                            " -y pkg10 pkg11"
                        ]
                    ]
                )
                + "\n"
                + textwrap.dedent(
                    """\
                    (12/13, 13/13) pkg12, pkg13:
                    A fix is available in UA Infra.
                    """
                )
                + MSG_SUBSCRIPTION,
            ),
            (  # No released version
                {
                    "pkg1": CVEPackageStatus(CVE_PKG_STATUS_IGNORED),
                    "pkg2": CVEPackageStatus(CVE_PKG_STATUS_IGNORED),
                    "pkg3": CVEPackageStatus(CVE_PKG_STATUS_PENDING),
                    "pkg4": CVEPackageStatus(CVE_PKG_STATUS_PENDING),
                    "pkg5": CVEPackageStatus(CVE_PKG_STATUS_NEEDS_TRIAGE),
                    "pkg6": CVEPackageStatus(CVE_PKG_STATUS_NEEDS_TRIAGE),
                    "pkg7": CVEPackageStatus(CVE_PKG_STATUS_NEEDED),
                    "pkg8": CVEPackageStatus(CVE_PKG_STATUS_NEEDED),
                    "pkg9": CVEPackageStatus(CVE_PKG_STATUS_DEFERRED),
                },
                {},
                {},
                "gcp",
                textwrap.dedent(
                    """\
                    9 affected packages are installed: {}
                    (1/9, 2/9, 3/9) pkg1, pkg2, pkg9:
                    Sorry, no fix is available.
                    (4/9, 5/9) pkg7, pkg8:
                    Sorry, no fix is available yet.
                    (6/9, 7/9) pkg5, pkg6:
                    Ubuntu security engineers are investigating this issue.
                    (8/9, 9/9) pkg3, pkg4:
                    A fix is coming soon. Try again tomorrow.
                    """
                ).format(
                    "pkg1, pkg2, pkg3, pkg4, pkg5, pkg6, pkg7, pkg8, pkg9"
                )
                + "{check} USN-### is not resolved.\n".format(check=FAIL_X),
            ),
        ),
    )
    @mock.patch("os.getuid", return_value=0)
    @mock.patch("uaclient.apt.run_apt_command", return_value="")
    @mock.patch("uaclient.security.get_cloud_type")
    @mock.patch("uaclient.security.util.prompt_choices", return_value="c")
    def test_messages_for_affected_packages_based_on_installed_and_usn_release(
        self,
        prompt_choices,
        get_cloud_type,
        m_run_apt_cmd,
        _m_os_getuid,
        affected_pkg_status,
        installed_packages,
        usn_released_pkgs,
        cloud_type,
        expected,
        FakeConfig,
        capsys,
    ):
        """Messaging is based on affected status and installed packages."""
        get_cloud_type.return_value = cloud_type
        cfg = FakeConfig()
        prompt_for_affected_packages(
            cfg=cfg,
            issue_id="USN-###",
            affected_pkg_status=affected_pkg_status,
            installed_packages=installed_packages,
            usn_released_pkgs=usn_released_pkgs,
        )
        out, err = capsys.readouterr()
        assert expected in out

    @pytest.mark.parametrize(
        "affected_pkg_status,installed_packages,usn_released_pkgs,expected",
        (
            (
                {
                    "pkg1": CVEPackageStatus(CVE_PKG_STATUS_RELEASED_ESM_APPS),
                    "pkg2": CVEPackageStatus(CVE_PKG_STATUS_RELEASED),
                    "pkg3": CVEPackageStatus(
                        CVE_PKG_STATUS_RELEASED_ESM_INFRA
                    ),
                },
                {
                    "pkg1": {"pkg1": "1.8"},
                    "pkg2": {"pkg2": "1.8"},
                    "pkg3": {"pkg3": "1.8"},
                },
                {
                    "pkg1": {"pkg1": {"version": "2.0"}},
                    "pkg2": {"pkg2": {"version": "2.0"}},
                    "pkg3": {"pkg3": {"version": "2.0"}},
                },
                textwrap.dedent(
                    """\
                    3 affected packages are installed: pkg1, pkg2, pkg3
                    (1/3) pkg2:
                    A fix is available in Ubuntu standard updates.
                    """
                )
                + colorize_commands(
                    [["apt update && apt install --only-upgrade" " -y pkg2"]]
                )
                + "\n"
                + textwrap.dedent(
                    """\
                    (2/3) pkg1:
                    A fix is available in UA Apps.
                    """
                )
                + MSG_SUBSCRIPTION
                + "\n"
                + PROMPT_ENTER_TOKEN
                + "\n"
                + colorize_commands([["ua attach token"]])
                + "\n"
                + colorize_commands(
                    [["apt update && apt install --only-upgrade" " -y pkg1"]]
                )
                + "\n"
                + textwrap.dedent(
                    """\
                    (3/3) pkg3:
                    A fix is available in UA Infra.
                    """
                )
                + colorize_commands(
                    [["apt update && apt install --only-upgrade" " -y pkg3"]]
                )
                + "\n"
                + "{check} USN-### is resolved.\n".format(check=OKGREEN_CHECK),
            ),
        ),
    )
    @mock.patch("uaclient.security._check_subscription_for_required_service")
    @mock.patch("uaclient.cli.action_attach")
    @mock.patch("builtins.input", return_value="token")
    @mock.patch("os.getuid", return_value=0)
    @mock.patch("uaclient.apt.run_apt_command", return_value="")
    @mock.patch("uaclient.security.get_cloud_type")
    @mock.patch("uaclient.security.util.prompt_choices", return_value="a")
    def test_messages_for_affected_packages_covering_all_release_pockets(
        self,
        m_prompt_choices,
        m_get_cloud_type,
        m_run_apt_cmd,
        _m_os_getuid,
        _m_input,
        m_action_attach,
        m_check_subscription,
        affected_pkg_status,
        installed_packages,
        usn_released_pkgs,
        expected,
        FakeConfig,
        capsys,
    ):
        m_get_cloud_type.return_value = "cloud"
        m_check_subscription.return_value = True

        def fake_attach(args, cfg):
            cfg.for_attached_machine()
            return 0

        m_action_attach.side_effect = fake_attach

        cfg = FakeConfig()
        prompt_for_affected_packages(
            cfg=cfg,
            issue_id="USN-###",
            affected_pkg_status=affected_pkg_status,
            installed_packages=installed_packages,
            usn_released_pkgs=usn_released_pkgs,
        )
        out, err = capsys.readouterr()
        assert expected in out

    @pytest.mark.parametrize(
        "affected_pkg_status,installed_packages,usn_released_pkgs,expected",
        (
            (
                {
                    "pkg1": CVEPackageStatus(CVE_PKG_STATUS_RELEASED),
                    "pkg2": CVEPackageStatus(CVE_PKG_STATUS_RELEASED_ESM_APPS),
                    "pkg3": CVEPackageStatus(
                        CVE_PKG_STATUS_RELEASED_ESM_INFRA
                    ),
                },
                {
                    "pkg1": {"pkg1": "1.8"},
                    "pkg2": {"pkg2": "1.8"},
                    "pkg3": {"pkg3": "1.8"},
                },
                {
                    "pkg1": {"pkg1": {"version": "2.0"}},
                    "pkg2": {"pkg2": {"version": "2.0"}},
                    "pkg3": {"pkg3": {"version": "2.0"}},
                },
                textwrap.dedent(
                    """\
                    3 affected packages are installed: pkg1, pkg2, pkg3
                    (1/3) pkg1:
                    A fix is available in Ubuntu standard updates.
                    """
                )
                + "{check} USN-### is not resolved.\n".format(check=FAIL_X),
            ),
        ),
    )
    @mock.patch("uaclient.security.upgrade_packages_and_attach")
    def test_messages_for_affected_packages_when_fix_fail(
        self,
        m_upgrade_packages,
        affected_pkg_status,
        installed_packages,
        usn_released_pkgs,
        expected,
        FakeConfig,
        capsys,
    ):
        m_upgrade_packages.return_value = False

        cfg = FakeConfig()
        prompt_for_affected_packages(
            cfg=cfg,
            issue_id="USN-###",
            affected_pkg_status=affected_pkg_status,
            installed_packages=installed_packages,
            usn_released_pkgs=usn_released_pkgs,
        )
        out, err = capsys.readouterr()
        assert expected in out

    @pytest.mark.parametrize(
        "service_status",
        (
            (UserFacingStatus.INACTIVE),
            (UserFacingStatus.INAPPLICABLE),
            (UserFacingStatus.UNAVAILABLE),
        ),
    )
    @pytest.mark.parametrize(
        "affected_pkg_status,installed_packages,usn_released_pkgs,expected",
        (
            (
                {
                    "pkg1": CVEPackageStatus(CVE_PKG_STATUS_RELEASED_ESM_APPS),
                    "pkg2": CVEPackageStatus(
                        CVE_PKG_STATUS_RELEASED_ESM_INFRA
                    ),
                },
                {"pkg1": {"pkg1": "1.8"}, "pkg2": {"pkg2": "1.8"}},
                {
                    "pkg1": {"pkg1": {"version": "2.0"}},
                    "pkg2": {"pkg2": {"version": "2.0"}},
                },
                textwrap.dedent(
                    """\
                    2 affected packages are installed: pkg1, pkg2
                    (1/2) pkg1:
                    A fix is available in UA Apps.
                    """
                )
                + MSG_SUBSCRIPTION
                + "\n"
                + PROMPT_ENTER_TOKEN
                + "\n"
                + colorize_commands([["ua attach token"]])
                + "\n"
                + MESSAGE_SECURITY_UA_SERVICE_NOT_ENTITLED.format(
                    service="esm-apps"
                )
                + "\n"
                + "{check} USN-### is not resolved.\n".format(check=FAIL_X),
            ),
        ),
    )
    @mock.patch("uaclient.cli.action_attach")
    @mock.patch("builtins.input", return_value="token")
    @mock.patch("os.getuid", return_value=0)
    @mock.patch("uaclient.security.get_cloud_type")
    @mock.patch("uaclient.security.util.prompt_choices", return_value="a")
    def test_messages_for_affected_packages_when_required_service_not_enabled(
        self,
        m_prompt_choices,
        m_get_cloud_type,
        _m_os_getuid,
        _m_input,
        m_action_attach,
        affected_pkg_status,
        installed_packages,
        usn_released_pkgs,
        expected,
        service_status,
        FakeConfig,
        capsys,
    ):
        import uaclient.security as sec

        m_get_cloud_type.return_value = "cloud"

        def fake_attach(args, cfg):
            cfg.for_attached_machine()
            return 0

        m_action_attach.side_effect = fake_attach
        m_entitlement_cls = mock.MagicMock()
        m_entitlement_obj = m_entitlement_cls.return_value
        m_entitlement_obj.user_facing_status.return_value = (
            service_status,
            "",
        )
        m_entitlement_obj.applicability_status.return_value = (
            ApplicabilityStatus.INAPPLICABLE,
            "",
        )
        type(m_entitlement_obj).name = mock.PropertyMock(
            return_value="esm-apps"
        )

        cfg = FakeConfig()
        with mock.patch.object(
            sec, "ENTITLEMENT_CLASS_BY_NAME", {"esm-apps": m_entitlement_cls}
        ):
            prompt_for_affected_packages(
                cfg=cfg,
                issue_id="USN-###",
                affected_pkg_status=affected_pkg_status,
                installed_packages=installed_packages,
                usn_released_pkgs=usn_released_pkgs,
            )
        out, err = capsys.readouterr()
        assert expected in out

    @pytest.mark.parametrize(
        "affected_pkg_status,installed_packages,usn_released_pkgs,expected",
        (
            (
                {"pkg1": CVEPackageStatus(CVE_PKG_STATUS_RELEASED_ESM_APPS)},
                {"pkg1": {"pkg1": "1.8"}},
                {"pkg1": {"pkg1": {"version": "2.0"}}},
                textwrap.dedent(
                    """\
                    1 affected package is installed: pkg1
                    (1/1) pkg1:
                    A fix is available in UA Apps.
                    """
                )
                + MESSAGE_SECURITY_SERVICE_DISABLED.format(service="esm-apps")
                + "\n"
                + colorize_commands([["ua enable esm-apps"]])
                + "\n"
                + colorize_commands(
                    [["apt update && apt install --only-upgrade" " -y pkg1"]]
                )
                + "\n"
                + "{check} USN-### is resolved.\n".format(check=OKGREEN_CHECK),
            ),
        ),
    )
    @mock.patch("uaclient.cli.action_enable", return_value=0)
    @mock.patch("uaclient.apt.run_apt_command", return_value="")
    @mock.patch("os.getuid", return_value=0)
    @mock.patch("uaclient.security.get_cloud_type")
    @mock.patch("uaclient.security.util.prompt_choices", return_value="e")
    def test_messages_for_affected_packages_when_service_can_be_enabled(
        self,
        m_prompt_choices,
        m_get_cloud_type,
        _m_os_getuid,
        _m_run_apt,
        m_action_enable,
        affected_pkg_status,
        installed_packages,
        usn_released_pkgs,
        expected,
        FakeConfig,
        capsys,
    ):
        import uaclient.security as sec

        m_get_cloud_type.return_value = "cloud"

        m_entitlement_cls = mock.MagicMock()
        m_entitlement_obj = m_entitlement_cls.return_value
        m_entitlement_obj.user_facing_status.return_value = (
            UserFacingStatus.INACTIVE,
            "",
        )
        m_entitlement_obj.applicability_status.return_value = (
            ApplicabilityStatus.APPLICABLE,
            "",
        )
        type(m_entitlement_obj).name = mock.PropertyMock(
            return_value="esm-apps"
        )

        cfg = FakeConfig()
        cfg.for_attached_machine()
        with mock.patch.object(
            sec, "ENTITLEMENT_CLASS_BY_NAME", {"esm-apps": m_entitlement_cls}
        ):
            prompt_for_affected_packages(
                cfg=cfg,
                issue_id="USN-###",
                affected_pkg_status=affected_pkg_status,
                installed_packages=installed_packages,
                usn_released_pkgs=usn_released_pkgs,
            )
        out, err = capsys.readouterr()
        print(out)
        print(expected)
        assert expected in out

    @pytest.mark.parametrize(
        "affected_pkg_status,installed_packages,usn_released_pkgs,expected",
        (
            (
                {"pkg1": CVEPackageStatus(CVE_PKG_STATUS_RELEASED_ESM_APPS)},
                {"pkg1": {"pkg1": "1.8"}},
                {"pkg1": {"pkg1": {"version": "2.0"}}},
                textwrap.dedent(
                    """\
                    1 affected package is installed: pkg1
                    (1/1) pkg1:
                    A fix is available in UA Apps.
                    """
                )
                + MESSAGE_SECURITY_SERVICE_DISABLED.format(service="esm-apps")
                + "\n"
                + MESSAGE_SECURITY_UA_SERVICE_NOT_ENABLED.format(
                    service="esm-apps"
                )
                + "\n"
                + "{check} USN-### is not resolved.\n".format(check=FAIL_X),
            ),
        ),
    )
    @mock.patch("os.getuid", return_value=0)
    @mock.patch("uaclient.security.get_cloud_type")
    @mock.patch("uaclient.security.util.prompt_choices", return_value="c")
    def test_messages_for_affected_packages_when_service_kept_disabled(
        self,
        m_prompt_choices,
        m_get_cloud_type,
        _m_os_getuid,
        affected_pkg_status,
        installed_packages,
        usn_released_pkgs,
        expected,
        FakeConfig,
        capsys,
    ):
        import uaclient.security as sec

        m_get_cloud_type.return_value = "cloud"

        m_entitlement_cls = mock.MagicMock()
        m_entitlement_obj = m_entitlement_cls.return_value
        m_entitlement_obj.user_facing_status.return_value = (
            UserFacingStatus.INACTIVE,
            "",
        )
        m_entitlement_obj.applicability_status.return_value = (
            ApplicabilityStatus.APPLICABLE,
            "",
        )
        type(m_entitlement_obj).name = mock.PropertyMock(
            return_value="esm-apps"
        )

        cfg = FakeConfig()
        cfg.for_attached_machine()
        with mock.patch.object(
            sec, "ENTITLEMENT_CLASS_BY_NAME", {"esm-apps": m_entitlement_cls}
        ):
            prompt_for_affected_packages(
                cfg=cfg,
                issue_id="USN-###",
                affected_pkg_status=affected_pkg_status,
                installed_packages=installed_packages,
                usn_released_pkgs=usn_released_pkgs,
            )
        out, err = capsys.readouterr()
        print(out)
        print(expected)
        assert expected in out


class TestUpgradePackagesAndAttach:
    @pytest.mark.parametrize("getuid_value", ((0), (1)))
    @mock.patch("os.getuid")
    @mock.patch("uaclient.security.util.subp")
    def test_upgrade_packages_are_installed_without_need_for_ua(
        self, m_subp, m_os_getuid, getuid_value, capsys
    ):
        m_subp.return_value = ("", "")
        m_os_getuid.return_value = getuid_value

        upgrade_packages_and_attach(
            cfg=None,
            upgrade_packages=["t1", "t2"],
            pocket="Ubuntu standard updates",
        )

        out, err = capsys.readouterr()
        if getuid_value == 0:
            assert m_subp.call_count == 2
            assert "apt update" in out
            assert "apt install --only-upgrade -y t1 t2" in out
        else:
            assert MESSAGE_SECURITY_APT_NON_ROOT in out
            assert m_subp.call_count == 0


class TestFixSecurityIssueId:
    @pytest.mark.parametrize(
        "issue_id", (("CVE-1800-123456"), ("USN-12345-12"))
    )
    def test_error_msg_when_issue_id_is_not_found(self, issue_id, FakeConfig):
        expected_message = "Error: {} not found.".format(issue_id)
        if "CVE" in issue_id:
            mock_func = "get_cve"
            issue_type = "CVE"
        else:
            mock_func = "get_notice"
            issue_type = "USN"

        with mock.patch.object(UrlError, "__str__") as m_str:
            with mock.patch.object(UASecurityClient, mock_func) as m_func:
                m_str.return_value = "NOT FOUND"
                msg = "{} with id 'ID' does not exist".format(issue_type)
                error_mock = mock.Mock()
                type(error_mock).url = mock.PropertyMock(return_value="URL")

                m_func.side_effect = SecurityAPIError(
                    e=error_mock, error_response={"message": msg}
                )

                with pytest.raises(exceptions.UserFacingError) as exc:
                    fix_security_issue_id(FakeConfig(), issue_id)

        assert expected_message == exc.value.msg

    @mock.patch("uaclient.security.query_installed_source_pkg_versions")
    @mock.patch("uaclient.security.get_usn_affected_packages_status")
    @mock.patch("uaclient.security.merge_usn_released_binary_package_versions")
    def test_error_msg_when_usn_does_not_define_any_cves(
        self,
        m_merge_usn,
        m_usn_affected_pkgs,
        m_query_installed_pkgs,
        FakeConfig,
    ):
        m_query_installed_pkgs.return_value = {}
        m_usn_affected_pkgs.return_value = {}
        m_merge_usn.return_value = {}
        with mock.patch.object(UASecurityClient, "get_notice") as m_notice:
            usn_mock = mock.MagicMock()
            type(usn_mock).release_packages = mock.PropertyMock(
                return_value={"a": {}}
            )
            type(usn_mock).cve_ids = mock.PropertyMock(return_value=[])
            m_notice.return_value = usn_mock

            with pytest.raises(exceptions.SecurityAPIMetadataError) as exc:
                fix_security_issue_id(FakeConfig(), "USN-123")

        expected_msg = "Error: USN-123 metadata defines no related CVEs."
        assert expected_msg in exc.value.msg

    @mock.patch("uaclient.security.query_installed_source_pkg_versions")
    @mock.patch("uaclient.security.get_usn_affected_packages_status")
    @mock.patch("uaclient.security.merge_usn_released_binary_package_versions")
    def test_error_msg_when_usn_does_not_have_any_related_usns(
        self,
        m_merge_usn,
        m_usn_affected_pkgs,
        m_query_installed_pkgs,
        FakeConfig,
    ):
        m_query_installed_pkgs.return_value = {}
        m_usn_affected_pkgs.return_value = {}
        m_merge_usn.return_value = {}
        with mock.patch.object(UASecurityClient, "get_notice") as m_notice:
            with mock.patch.object(
                UASecurityClient, "get_notices"
            ) as m_notices:
                usn_mock = mock.MagicMock()
                type(usn_mock).response = mock.PropertyMock(
                    return_value={"release_packages": {}}
                )
                type(usn_mock).cve_ids = mock.PropertyMock(
                    return_value=["cve-123"]
                )
                type(usn_mock).id = mock.PropertyMock(return_value="id")

                m_notice.return_value = usn_mock
                m_notices.return_value = [usn_mock]

                with pytest.raises(exceptions.SecurityAPIMetadataError) as exc:
                    fix_security_issue_id(FakeConfig(), "USN-123")

        expected_msg = (
            "Error: USN-123 metadata defines no fixed package versions."
        )
        assert expected_msg in exc.value.msg


class TestMergeUSNReleasedBinaryPackageVersions:
    @pytest.mark.parametrize(
        "usns_released_packages, expected_pkgs_dict",
        (
            ([{}], {}),
            (
                [{"pkg1": {"libpkg1": {"version": "1.0", "name": "libpkg1"}}}],
                {"pkg1": {"libpkg1": {"version": "1.0", "name": "libpkg1"}}},
            ),
            (
                [
                    {
                        "pkg1": {
                            "libpkg1": {"version": "1.0", "name": "libpkg1"}
                        },
                        "pkg2": {
                            "libpkg2": {"version": "2.0", "name": "libpkg2"},
                            "libpkg3": {"version": "3.0", "name": "libpkg3"},
                            "libpkg4": {"version": "3.0", "name": "libpkg4"},
                        },
                    },
                    {
                        "pkg2": {
                            "libpkg2": {"version": "1.8", "name": "libpkg2"},
                            "libpkg4": {"version": "3.2", "name": "libpkg4"},
                        }
                    },
                ],
                {
                    "pkg1": {"libpkg1": {"version": "1.0", "name": "libpkg1"}},
                    "pkg2": {
                        "libpkg2": {"version": "2.0", "name": "libpkg2"},
                        "libpkg3": {"version": "3.0", "name": "libpkg3"},
                        "libpkg4": {"version": "3.2", "name": "libpkg4"},
                    },
                },
            ),
            (
                [
                    {
                        "pkg1": {
                            "libpkg1": {"version": "1.0", "name": "libpkg1"},
                            "source": {"version": "2.0", "name": "pkg1"},
                        }
                    },
                    {"pkg1": {"source": {"version": "2.5", "name": "pkg1"}}},
                ],
                {
                    "pkg1": {
                        "libpkg1": {"version": "1.0", "name": "libpkg1"},
                        "source": {"version": "2.5", "name": "pkg1"},
                    }
                },
            ),
        ),
    )
    def test_merge_usn_released_binary_package_versions(
        self, usns_released_packages, expected_pkgs_dict
    ):
        usns = []
        for usn_released_pkgs in usns_released_packages:
            usn = mock.MagicMock()
            type(usn).release_packages = mock.PropertyMock(
                return_value=usn_released_pkgs
            )
            usns.append(usn)

        usn_pkgs_dict = merge_usn_released_binary_package_versions(usns)
        assert expected_pkgs_dict == usn_pkgs_dict


class TestOverrideUSNReleasePackageStatus:
    @pytest.mark.parametrize(
        "pkg_status",
        (
            CVE_PKG_STATUS_IGNORED,
            CVE_PKG_STATUS_PENDING,
            CVE_PKG_STATUS_NEEDS_TRIAGE,
            CVE_PKG_STATUS_NEEDED,
            CVE_PKG_STATUS_DEFERRED,
            CVE_PKG_STATUS_RELEASED,
            CVE_PKG_STATUS_RELEASED_ESM_INFRA,
        ),
    )
    @pytest.mark.parametrize(
        "usn_src_released_pkgs,expected",
        (
            ({}, None),
            (  # No "source" key, so ignore all binaries
                {"somebinary": {"pocket": "my-pocket", "version": "usn-ver"}},
                None,
            ),
            (
                {
                    "source": {
                        "name": "srcpkg",
                        "version": "usn-source-pkg-ver",
                    },
                    "somebinary": {
                        "pocket": "my-pocket",
                        "version": "usn-bin-ver",
                    },
                },
                {
                    "pocket": "my-pocket",
                    "description": "usn-source-pkg-ver",
                    "status": "released",
                },
            ),
        ),
    )
    def test_override_cve_src_info_with_pocket_and_ver_from_usn(
        self, usn_src_released_pkgs, expected, pkg_status
    ):
        """Override CVEPackageStatus with released/pocket from USN."""
        orig_cve = CVEPackageStatus(pkg_status)
        override = override_usn_release_package_status(
            orig_cve, usn_src_released_pkgs
        )
        if expected is None:  # Expect CVEPackageStatus unaltered
            assert override.response == orig_cve.response
        else:
            assert expected == override.response
