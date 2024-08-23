import copy
from collections import defaultdict

import mock
import pytest

from uaclient import exceptions, http
from uaclient.api.u.pro.security.fix._common import (
    API_V1_CVE_TMPL,
    API_V1_CVES,
    API_V1_NOTICE_TMPL,
    API_V1_NOTICES,
    CVE,
    USN,
    CVEPackageStatus,
    UASecurityClient,
    get_cve_affected_source_packages_status,
    get_related_usns,
    get_usn_affected_packages_status,
    merge_usn_released_binary_package_versions,
    override_usn_release_package_status,
    query_installed_source_pkg_versions,
)

M_PATH = "uaclient.api.u.pro.security.fix._common."

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
    "cves": "cve",
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
    "notices_ids": ["USN-4510-1", "USN-4510-2", "USN-4559-1"],
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
    "cves_ids": ["CVE-2020-1473", "CVE-2020-1472"],
    "id": "USN-4510-2",
    "instructions": "In general, a standard system update will make all ...\n",
    "references": [],
    "release_packages": {
        "series-example-1": [
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
        "series-example-2": [
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


SAMPLE_USN_RESPONSE_NO_CVES = {
    "cves_ids": [],
    "id": "USN-4038-3",
    "instructions": "In general, a standard system update will make all ...\n",
    "references": ["https://launchpad.net/bugs/1834494"],
    "release_packages": {
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
                "pocket": "security",
            },
        ]
    },
    "summary": "",
    "title": "USN vulnerability",
    "type": "USN",
}

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


def shallow_merge_dicts(a, b):
    c = a.copy()
    c.update(b)
    return c


class TestCVE:
    def test_cve_init_attributes(self, FakeConfig):
        """CVE.__init__ saves client and response on instance."""
        client = UASecurityClient(FakeConfig())
        cve = CVE(client, {"some": "response"})
        assert client == cve.client
        assert {"some": "response"} == cve.response

    @pytest.mark.parametrize(
        "cve1,cve2,are_equal",
        (
            (CVE(None, {"1": "2"}), CVE(None, {"1": "2"}), True),
            (CVE("A", {"1": "2"}), CVE("B", {"1": "2"}), True),
            (CVE(None, {}), CVE("B", {"1": "2"}), False),
            (CVE(None, {"1": "2"}), USN(None, {"1": "2"}), False),
        ),
    )
    def test_equality(self, cve1, cve2, are_equal):
        """Equality is based instance type and CVE.response value"""
        if are_equal:
            assert cve1.response == cve2.response
            assert cve1 == cve2
        else:
            if isinstance(cve1, CVE) and isinstance(cve2, CVE):
                assert cve1.response != cve2.response
            assert cve1 != cve2

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
            ("notices_ids", [], {}),
            ("notices_ids", [], {"notices_ids": []}),
            ("notices_ids", ["1", "2"], {"notices_ids": ["1", "2"]}),
        ),
    )
    def test_cve_basic_properties_from_response(
        self, attr_name, expected, response, FakeConfig
    ):
        """CVE instance properties are set from Security API CVE response."""
        client = UASecurityClient(FakeConfig())
        cve = CVE(client, response)
        assert expected == getattr(cve, attr_name)

    @pytest.mark.parametrize(
        "usns_response,expected",
        (
            (None, []),
            ([], []),
            (  # USNs are properly sorted by id
                [{"id": "USN-1"}, {"id": "USN-2"}, {"id": "LSN-3"}],
                [USN(None, {"id": "USN-2"}), USN(None, {"id": "USN-1"})],
            ),
        ),
    )
    def test_notices_cached_from_usns_response(
        self, usns_response, expected, FakeConfig
    ):
        """List of USNs returned from CVE 'usns' response if present."""
        client = UASecurityClient(FakeConfig())
        cve_response = copy.deepcopy(SAMPLE_CVE_RESPONSE)
        if usns_response is not None:
            cve_response["notices"] = usns_response
        cve = CVE(client, cve_response)
        assert expected == cve.notices
        # clear box test caching in effect
        cve.response = "junk"
        assert expected == cve.notices


class TestUSN:
    def test_usn_init_attributes(self, FakeConfig):
        """USN.__init__ saves client and response on instance."""
        client = UASecurityClient(FakeConfig())
        cve = USN(client, {"some": "response"})
        assert client == cve.client
        assert {"some": "response"} == cve.response

    @pytest.mark.parametrize(
        "usn1,usn2,are_equal",
        (
            (USN(None, {"1": "2"}), USN(None, {"1": "2"}), True),
            (USN("A", {"1": "2"}), USN("B", {"1": "2"}), True),
            (USN(None, {}), USN("B", {"1": "2"}), False),
            (USN(None, {"1": "2"}), CVE(None, {"1": "2"}), False),
        ),
    )
    def test_equality(self, usn1, usn2, are_equal):
        """Equality is based instance type and USN.response value"""
        if are_equal:
            assert usn1.response == usn2.response
            assert usn1 == usn2
        else:
            if isinstance(usn1, USN) and isinstance(usn2, USN):
                assert usn1.response != usn2.response
            assert usn1 != usn2

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
            ("cves_ids", [], {}),
            ("cves_ids", [], {"cves_ids": []}),
            ("cves_ids", ["1", "2"], {"cves_ids": ["1", "2"]}),
            ("cves", [], {}),
            ("cves", [], {"cves": []}),
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
                "series-example-1",
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
                "series-example-2",
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
            ("series-example-3", {}),
        ),
    )
    @mock.patch("uaclient.system.get_release_info")
    def test_release_packages_returns_source_and_binary_pkgs_for_series(
        self, m_get_release_info, series, expected, FakeConfig
    ):
        m_get_release_info.return_value = mock.MagicMock(series=series)
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
                (
                    "Metadata for USN-4510-2 is invalid. "
                    "Error: USN-4510-2 metadata does not define "
                    "release_packages source_link for samba2."
                ),
            ),
            (
                "unknown format",
                (
                    "Metadata for USN-4510-2 is invalid. "
                    "Error: USN-4510-2 metadata has unexpected "
                    "release_packages source_link value for samba2: "
                    "unknown format."
                ),
            ),
        ),
    )
    @mock.patch("uaclient.system.get_release_info")
    def test_release_packages_errors_on_sparse_source_url(
        self, m_get_release_info, source_link, error_msg, FakeConfig
    ):
        """Raise errors when USN metadata contains no valid source_link."""
        m_get_release_info.return_value = mock.MagicMock(
            series="series-example-1"
        )
        client = UASecurityClient(FakeConfig())
        sparse_md = copy.deepcopy(SAMPLE_USN_RESPONSE)
        sparse_md["release_packages"]["series-example-1"].append(
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
        assert error_msg in str(exc.value)

    @pytest.mark.parametrize(
        "cves_response,expected",
        (
            (None, []),
            ([], []),
            (  # CVEs are properly sorted by id
                [{"id": "1"}, {"id": "2"}],
                [CVE(None, {"id": "2"}), CVE(None, {"id": "1"})],
            ),
        ),
    )
    def test_cves_cached_and_sorted_from_cves_response(
        self, cves_response, expected, FakeConfig
    ):
        """List of USNs returned from CVE 'usns' response if present."""
        client = UASecurityClient(FakeConfig())
        usn_response = copy.deepcopy(SAMPLE_USN_RESPONSE)
        if cves_response is not None:
            usn_response["cves"] = cves_response
        usn = USN(client, usn_response)
        assert expected == usn.cves
        # clear box test caching in effect
        usn.response = "junk"
        assert expected == usn.cves


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
            ("esm-infra", "1.2", "Ubuntu Pro: ESM Infra"),
            ("esm-apps", "1.2", "Ubuntu Pro: ESM Apps"),
            ("updates", "1.2esm", "Ubuntu standard updates"),
            ("security", "1.2esm", "Ubuntu standard updates"),
            (None, "1.2", "Ubuntu standard updates"),
            (None, "1.2esm", "Ubuntu Pro: ESM Infra"),
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
    def test_requires_pro_from_response(self, pocket, description, expected):
        """requires_pro is derived from response pocket and description."""
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
            (
                "released",
                "esm-infra",
                "A fix is available in Ubuntu Pro: ESM Infra.",
            ),
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


@mock.patch(M_PATH + "UASecurityClient.request_url")
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
            ) in str(exc.value)
            assert 0 == request_url.call_count
        else:
            for key in SAMPLE_GET_CVES_QUERY_PARAMS:
                if key not in m_kwargs:
                    m_kwargs[key] = None
            request_url.return_value = http.HTTPResponse(
                code=200,
                headers={},
                body="",
                json_dict={},
                json_list=["body1", "body2"],
            )
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
            ({"cves": "cve"}, None, None),
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
            ) in str(exc.value)
            assert 0 == request_url.call_count
        else:
            for key in SAMPLE_GET_NOTICES_QUERY_PARAMS:
                if key not in m_kwargs:
                    m_kwargs[key] = None
            request_url.return_value = http.HTTPResponse(
                code=200,
                headers={},
                body="",
                json_dict={
                    "notices": [
                        {"id": "USN-2", "cves_ids": ["cve"]},
                        {"id": "USN-1", "cves_ids": ["cve"]},
                        {"id": "LSN-3", "cves_ids": ["cve"]},
                    ]
                },
                json_list=[],
            )
            [usn1, usn2] = client.get_notices(**m_kwargs)
            assert isinstance(usn1, USN)
            assert isinstance(usn2, USN)
            assert "USN-1" == usn1.id
            assert "USN-2" == usn2.id
            assert [
                mock.call(API_V1_NOTICES, query_params=m_kwargs)
            ] == request_url.call_args_list

    @pytest.mark.parametrize("cves", (("cve1"), (None)))
    def test_get_notices_filter_usns_when_setting_cves_param(
        self, request_url, cves, FakeConfig
    ):
        """Test if cves are used to filter the returned USNs."""
        cfg = FakeConfig()
        client = UASecurityClient(cfg)
        request_url.return_value = http.HTTPResponse(
            code=200,
            headers={},
            body="",
            json_dict={
                "notices": [
                    {"id": "USN-2", "cves_ids": ["cve2"]},
                    {"id": "USN-1", "cves_ids": ["cve1"]},
                    {"id": "LSN-3", "cves_ids": ["cve3"]},
                ]
            },
            json_list=[],
        )
        usns = client.get_notices(cves=cves)

        if cves:
            assert len(usns) == 1
            assert usns[0].id == "USN-1"
        else:
            assert len(usns) == 2
            assert usns[0].id == "USN-1"
            assert usns[1].id == "USN-2"

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
            ) in str(exc.value)
            assert 0 == request_url.call_count
        else:
            request_url.return_value = http.HTTPResponse(
                code=200,
                headers={},
                body="",
                json_dict={"body": "body"},
                json_list=[],
            )
            cve = client.get_cve(**m_kwargs)
            assert isinstance(cve, CVE)
            assert {"body": "body"} == cve.response
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
            ) in str(exc.value)
            assert 0 == request_url.call_count
        else:
            request_url.return_value = http.HTTPResponse(
                code=200,
                headers={},
                body="",
                json_dict={"body": "body"},
                json_list=[],
            )
            assert {"body": "body"} == client.get_notice(**m_kwargs).response
            assert [
                mock.call(
                    API_V1_NOTICE_TMPL.format(notice=m_kwargs["notice_id"])
                )
            ] == request_url.call_args_list


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
    @mock.patch("uaclient.system.get_release_info")
    def test_affected_packages_status_filters_by_installed_pkgs_and_series(
        self,
        m_get_release_info,
        series,
        installed_packages,
        expected_status,
        FakeConfig,
    ):
        """Package statuses are filtered if not installed"""
        m_get_release_info.return_value = mock.MagicMock(series=series)
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
    @mock.patch(M_PATH + "system.subp")
    @mock.patch("uaclient.system.get_release_info")
    def test_result_keyed_by_source_package_name(
        self, m_get_release_info, subp, dpkg_out, results
    ):
        m_get_release_info.return_value = mock.MagicMock(series="bionic")
        subp.return_value = dpkg_out, ""
        assert results == query_installed_source_pkg_versions()
        _format = "-f=${Package},${Source},${Version},${db:Status-Status}\n"
        assert [
            mock.call(["dpkg-query", _format, "-W"])
        ] == subp.call_args_list


class TestGetRelatedUSNs:
    def test_no_usns_returned_when_no_cves_are_found(self, FakeConfig):
        cfg = FakeConfig()
        client = UASecurityClient(cfg=cfg)
        usn = USN(client, SAMPLE_USN_RESPONSE_NO_CVES)

        assert [] == get_related_usns(usn, client)

    def test_usns_ignore_non_usns_items(self, FakeConfig):
        expected_value = mock.MagicMock(id="USN-1235-1")

        def fake_get_notice(notice_id):
            return expected_value

        m_client = mock.MagicMock()
        m_client.get_notice.side_effect = fake_get_notice

        m_usn = mock.MagicMock(
            cves=[
                mock.MagicMock(
                    notices_ids=["USN-1235-1", "LSN-0088-1"],
                )
            ],
            id="USN-8796-1",
        )

        assert [expected_value] == get_related_usns(m_usn, m_client)


class TestGetUSNAffectedPackagesStatus:
    @pytest.mark.parametrize(
        "installed_packages, affected_packages",
        (
            (
                {"coin3": {"libcoin80-runtime", "1.0"}},
                {
                    "coin3": CVEPackageStatus(
                        defaultdict(
                            str, {"status": "released", "pocket": "security"}
                        )
                    )
                },
            ),
        ),
    )
    @mock.patch("uaclient.system.get_release_info")
    def test_pkgs_come_from_release_packages_if_usn_has_no_cves(
        self,
        m_get_release_info,
        installed_packages,
        affected_packages,
        FakeConfig,
    ):
        m_get_release_info.return_value = mock.MagicMock(series="bionic")

        cfg = FakeConfig()
        client = UASecurityClient(cfg=cfg)
        usn = USN(client, SAMPLE_USN_RESPONSE_NO_CVES)
        actual_value = get_usn_affected_packages_status(
            usn, installed_packages
        )

        if not affected_packages:
            assert actual_value is {}
        else:
            assert "coin3" in actual_value
            assert (
                affected_packages["coin3"].status
                == actual_value["coin3"].status
            )
            assert (
                affected_packages["coin3"].pocket_source
                == actual_value["coin3"].pocket_source
            )


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
            (
                [
                    {
                        "pkg1": {
                            "libpkg1": {"version": "1.0", "name": "libpkg1"},
                            "source": {"version": "2.0", "name": "pkg1"},
                        },
                        "pkg2": {
                            "libpkg2": {
                                "version": "2.0",
                                "name": "libpkg2",
                                "pocket": "esm-apps",
                            },
                            "source": {
                                "version": "2.0",
                                "name": "pkg2",
                                "pocket": "esm-apps",
                            },
                        },
                    }
                ],
                {
                    "pkg1": {
                        "libpkg1": {"version": "1.0", "name": "libpkg1"},
                        "source": {"version": "2.0", "name": "pkg1"},
                    }
                },
            ),
        ),
    )
    def test_merge_usn_released_binary_package_versions(
        self, usns_released_packages, expected_pkgs_dict, _subp
    ):
        usns = []
        beta_packages = {"esm-infra": False, "esm-apps": True}

        for usn_released_pkgs in usns_released_packages:
            usn = mock.MagicMock()
            type(usn).release_packages = mock.PropertyMock(
                return_value=usn_released_pkgs
            )
            usns.append(usn)

        with mock.patch("uaclient.system._subp", side_effect=_subp):
            usn_pkgs_dict = merge_usn_released_binary_package_versions(
                usns, beta_packages
            )
        assert expected_pkgs_dict == usn_pkgs_dict
