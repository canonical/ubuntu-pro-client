import mock
import pytest

from uaclient.security import (
    API_V1_CVES,
    API_V1_CVE_TMPL,
    API_V1_NOTICES,
    API_V1_NOTICE_TMPL,
    CVE,
    CVEPackageStatus,
    UASecurityClient,
    USN,
    query_installed_source_pkg_versions,
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


@mock.patch("uaclient.serviceclient.UAServiceClient.request_url")
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
