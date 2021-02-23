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
    get_cve_affected_packages_status,
    query_installed_source_pkg_versions,
    version_cmp_le,
)


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
    "cves": ["CVE-2020-1472"],
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
                "version": "2:4.3.11+dfsg-0ubuntu0.14.04.20+esm9",
                "version_link": "https://....11+dfsg-0ubuntu0.14.04.20+esm9",
            },
        ]
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
            # not-affected status has a bearing on status filtering
            ("focal", {"samba": "1000"}, {}),
        ),
    )
    @mock.patch("uaclient.security.util.get_platform_info")
    def test_affected_packages_status_filters_installed_pkgs_and_not_affected(
        self,
        get_platform_info,
        series,
        installed_packages,
        expected_status,
        FakeConfig,
    ):
        """Package statuses are filterd if not installed or == not-affected"""
        get_platform_info.return_value = {"series": series}
        client = UASecurityClient(FakeConfig())
        cve = CVE(client, SAMPLE_CVE_RESPONSE)
        affected_packages = get_cve_affected_packages_status(
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
        """CVE.get_notices_metadata is cached to avoid API round-trips."""
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
        assert ["CVE-2020-1472"] == [cve.id for cve in cves]
        assert [
            mock.call("cves/CVE-2020-1472.json")
        ] == request_url.call_args_list
        # no extra calls being made
        usn.get_cves_metadata()
        assert 1 == request_url.call_count

    def test_get_url_header(self, FakeConfig):
        """USN.get_url_header returns a string based on the USN response."""
        client = UASecurityClient(FakeConfig())
        usn = CVE(client, SAMPLE_USN_RESPONSE)
        assert (
            textwrap.dedent(
                """USN-4510-2: None\nhttps://ubuntu.com/security/USN-4510-2"""
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
        "status,pocket,expected",
        (
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


# @mock.patch("uaclient.serviceclient.UAServiceClient.request_url")
@mock.patch("uaclient.security.UASecurityClient.request_url")
class TestUASecurityClient:
    @pytest.mark.parametrize(
        "m_kwargs,expected_error",
        (
            ({}, None),
            ({"query": "vq"}, None),
            (SAMPLE_GET_CVES_QUERY_PARAMS, None),
            ({"invalidparam": "vv"}, TypeError),
        ),
    )
    def test_get_cves_sets_query_params_on_get_cves_route(
        self, request_url, m_kwargs, expected_error, FakeConfig
    ):
        """GET CVE instances from API_V1_CVES route with querystrings"""
        client = UASecurityClient(FakeConfig())
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
        "m_kwargs,expected_error",
        (
            ({}, None),
            ({"details": "vd"}, None),
            (SAMPLE_GET_NOTICES_QUERY_PARAMS, None),
            ({"invalidparam": "vv"}, TypeError),
        ),
    )
    def test_get_notices_sets_query_params_on_get_cves_route(
        self, request_url, m_kwargs, expected_error, FakeConfig
    ):
        """GET body from API_V1_NOTICES route with appropriate querystring"""
        client = UASecurityClient(FakeConfig())
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
            request_url.return_value = (["body1", "body2"], "headers")
            [usn1, usn2] = client.get_notices(**m_kwargs)
            assert isinstance(usn1, USN)
            assert isinstance(usn2, USN)
            assert "body1" == usn1.response
            assert "body2" == usn2.response
            assert [
                mock.call(API_V1_NOTICES, query_params=m_kwargs)
            ] == request_url.call_args_list

    @pytest.mark.parametrize(
        "m_kwargs,expected_error",
        (({}, TypeError), ({"cve_id": "CVE-1"}, None)),
    )
    def test_get_cve_provides_response_from_cve_json_route(
        self, request_url, m_kwargs, expected_error, FakeConfig
    ):
        """GET body from API_V1_CVE_TMPL route with required cve_id."""
        client = UASecurityClient(FakeConfig())
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
        "m_kwargs,expected_error",
        (({}, TypeError), ({"notice_id": "USN-1"}, None)),
    )
    def test_get_notice_provides_response_from_notice_json_route(
        self, request_url, m_kwargs, expected_error, FakeConfig
    ):
        """GET body from API_V1_NOTICE_TMPL route with required notice_id."""
        client = UASecurityClient(FakeConfig())
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
            (
                "a,1.2,installed\nzip,3.0-1,installed\nb,1.2,config-files",
                {"a": "1.2", "zip": "3.0-1"},
            ),
        ),
    )
    @mock.patch("uaclient.security.util.subp")
    def test_result_keyed_by_source_package_name(
        self, subp, dpkg_out, results
    ):
        subp.return_value = dpkg_out, ""
        assert results == query_installed_source_pkg_versions()
        assert [
            mock.call(
                [
                    "dpkg-query",
                    "-f=${Source},${Version},${db:Status-Status}\n",
                    "-W",
                ]
            )
        ] == subp.call_args_list
