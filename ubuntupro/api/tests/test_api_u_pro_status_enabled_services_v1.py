import mock

from ubuntupro import entitlements
from ubuntupro.api.u.pro.status.enabled_services.v1 import (
    EnabledService,
    _enabled_services,
)
from ubuntupro.entitlements.entitlement_status import UserFacingStatus


class TestEnabledServicesV1:
    @mock.patch("ubuntupro.api.u.pro.status.enabled_services.v1._is_attached")
    def test_enabled_services(self, m_is_attached):
        m_is_attached.return_value = mock.MagicMock(is_attached=True)

        m_cls_1 = mock.MagicMock()
        m_inst_1 = mock.MagicMock(variants={})
        type(m_inst_1).name = mock.PropertyMock(return_value="ent1")
        m_inst_1.user_facing_status.return_value = (
            UserFacingStatus.ACTIVE,
            "",
        )
        m_cls_1.return_value = m_inst_1

        m_variant_cls = mock.MagicMock()
        m_variant_inst = mock.MagicMock(variant_name="variant")
        m_variant_inst.user_facing_status.return_value = (
            UserFacingStatus.ACTIVE,
            "",
        )
        m_variant_cls.return_value = m_variant_inst

        m_cls_2 = mock.MagicMock()
        m_inst_2 = mock.MagicMock(variants={"variant": m_variant_cls})
        type(m_inst_2).name = mock.PropertyMock(return_value="ent2")
        m_inst_2.user_facing_status.return_value = (
            UserFacingStatus.ACTIVE,
            "",
        )
        m_cls_2.return_value = m_inst_2

        m_cls_3 = mock.MagicMock()
        m_inst_3 = mock.MagicMock()
        type(m_inst_3).name = mock.PropertyMock(return_value="ent3")
        m_inst_3.user_facing_status.return_value = (
            UserFacingStatus.INACTIVE,
            "",
        )

        ents = [m_cls_1, m_cls_2, m_cls_3]
        expected_enabled_services = [
            EnabledService(name="ent1"),
            EnabledService(
                name="ent2",
                variant_enabled=True,
                variant_name="variant",
            ),
        ]

        with mock.patch.object(entitlements, "ENTITLEMENT_CLASSES", ents):
            actual_enabled_services = _enabled_services(
                cfg=mock.MagicMock()
            ).enabled_services

        assert 1 == m_is_attached.call_count
        assert expected_enabled_services == actual_enabled_services

    @mock.patch("ubuntupro.api.u.pro.status.enabled_services.v1._is_attached")
    def test_enabled_services_when_unattached(self, m_is_attached):
        m_is_attached.return_value = mock.MagicMock(is_attached=False)

        assert [] == _enabled_services(cfg=mock.MagicMock()).enabled_services
        assert 1 == m_is_attached.call_count
