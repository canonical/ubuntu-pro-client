import mock

from uaclient.api.u.pro.security.status.livepatch_cves.v1 import (
    LivepatchCVEsResult,
    _livepatch_cves,
)

M_PATH = "uaclient.api.u.pro.security.status.livepatch_cves.v1."


@mock.patch(M_PATH + "get_livepatch_fixed_cves")
class TestLivepatchCvesV1:
    def test_empty_livepatch_cves(self, m_cves, FakeConfig):
        m_cves.return_value = []
        result = _livepatch_cves(cfg=FakeConfig())
        assert isinstance(result, LivepatchCVEsResult)
        assert result.fixed_cves == []

    def test_livepatch_cves(self, m_cves, FakeConfig):
        m_cves.return_value = [
            {"name": "CVE-123456", "patched": True},
            {"name": "CVE-45678", "patched": False},
        ]
        result = _livepatch_cves(cfg=FakeConfig())
        assert isinstance(result, LivepatchCVEsResult)
        assert len(result.fixed_cves) == 2
        assert result.fixed_cves[0].name == "CVE-123456"
        assert result.fixed_cves[0].patched is True
        assert result.fixed_cves[1].name == "CVE-45678"
        assert result.fixed_cves[1].patched is False
