import mock
import pytest

from uaclient import messages
from uaclient.entitlements.entitlement_status import ApplicabilityStatus
from uaclient.entitlements.realtime import IntelIotgRealtime
from uaclient.system import CpuInfo

RT_PATH = "uaclient.entitlements.realtime.RealtimeKernelEntitlement."


class TestIntelIOTGVariannt:
    @pytest.mark.parametrize(
        "cpu_info,expected_status,expected_msg",
        (
            (
                CpuInfo(vendor_id="test", model=None, stepping=None),
                ApplicabilityStatus.INAPPLICABLE,
                messages.INAPPLICABLE_VENDOR_NAME.format(
                    title=IntelIotgRealtime.title,
                    vendor="test",
                    supported_vendors="intel",
                ),
            ),
            (
                CpuInfo(vendor_id="intel", model=None, stepping=None),
                ApplicabilityStatus.APPLICABLE,
                None,
            ),
        ),
    )
    @mock.patch("uaclient.system.get_kernel_info")
    @mock.patch("uaclient.system.get_cpu_info")
    def test_applicability_status(
        self,
        m_get_cpu_info,
        _m_get_kernel_info,
        cpu_info,
        expected_status,
        expected_msg,
        FakeConfig,
    ):
        m_get_cpu_info.return_value = cpu_info
        ent = IntelIotgRealtime(FakeConfig())
        with mock.patch.object(
            ent, "_base_entitlement_cfg"
        ) as m_entitlement_cfg:
            m_entitlement_cfg.return_value = {
                "entitlement": {
                    "affordances": {
                        "vendor_names": ["intel"],
                    }
                }
            }
            actual_status, actual_msg = ent.applicability_status()
            assert (
                expected_status,
                expected_msg,
            ) == ent.applicability_status()
