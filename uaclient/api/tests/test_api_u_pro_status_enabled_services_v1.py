import mock

from uaclient import entitlements
from uaclient.api.data_types import ErrorWarningObject
from uaclient.api.u.pro.status.enabled_services.v1 import (
    EnabledService,
    _enabled_services,
)
from uaclient.entitlements.entitlement_status import UserFacingStatus
from uaclient.messages import NamedMessage


class TestEnabledServicesV1:
    @mock.patch("uaclient.api.u.pro.status.enabled_services.v1._is_attached")
    def test_enabled_services(self, m_is_attached):
        m_is_attached.return_value = mock.MagicMock(is_attached=True)

        m_cls_1 = mock.MagicMock()
        type(m_cls_1).name = mock.PropertyMock(return_value="ent1")
        m_inst_1 = mock.MagicMock(variants={})
        type(m_inst_1).name = mock.PropertyMock(return_value="ent1")
        type(m_inst_1).presentation_name = mock.PropertyMock(
            return_value="ent1"
        )
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
        type(m_cls_2).name = mock.PropertyMock(return_value="ent2")
        m_inst_2 = mock.MagicMock(variants={"variant": m_variant_cls})
        type(m_inst_2).name = mock.PropertyMock(return_value="ent2")
        type(m_inst_2).presentation_name = mock.PropertyMock(
            return_value="ent2"
        )
        m_inst_2.user_facing_status.return_value = (
            UserFacingStatus.ACTIVE,
            "",
        )
        m_cls_2.return_value = m_inst_2

        m_cls_3 = mock.MagicMock()
        type(m_cls_3).name = mock.PropertyMock(return_value="ent3")
        m_inst_3 = mock.MagicMock()
        type(m_inst_3).name = mock.PropertyMock(return_value="ent3")
        type(m_inst_3).presentation_name = mock.PropertyMock(
            return_value="ent3"
        )
        m_inst_3.user_facing_status.return_value = (
            UserFacingStatus.INACTIVE,
            "",
        )
        m_cls_3.return_value = m_inst_3

        m_cls_4 = mock.MagicMock()
        type(m_cls_4).name = mock.PropertyMock(return_value="ent4")
        m_inst_4 = mock.MagicMock()
        type(m_inst_4).name = mock.PropertyMock(return_value="ent4")
        type(m_inst_4).presentation_name = mock.PropertyMock(
            return_value="ent4"
        )
        m_inst_4.user_facing_status.return_value = (
            UserFacingStatus.INAPPLICABLE,
            "",
        )
        m_cls_4.return_value = m_inst_4

        m_cls_5 = mock.MagicMock()
        type(m_cls_5).name = mock.PropertyMock(return_value="ent5")
        m_inst_5 = mock.MagicMock()
        type(m_inst_5).name = mock.PropertyMock(return_value="ent5")
        type(m_inst_5).presentation_name = mock.PropertyMock(
            return_value="ent5"
        )
        m_inst_5.user_facing_status.return_value = (
            UserFacingStatus.WARNING,
            NamedMessage(name="warning_code", msg="warning_msg"),
        )
        m_cls_5.return_value = m_inst_5

        ents = [m_cls_1, m_cls_2, m_cls_3, m_cls_4, m_cls_5]
        expected_enabled_services = [
            EnabledService(name="ent1"),
            EnabledService(
                name="ent2",
                variant_enabled=True,
                variant_name="variant",
            ),
            EnabledService(name="ent5"),
        ]

        expected_warnings = [
            ErrorWarningObject(
                title="warning_msg",
                code="warning_code",
                meta={"service": "ent5"},
            )
        ]

        with mock.patch.object(entitlements, "ENTITLEMENT_CLASSES", ents):
            enabled_services_ret = _enabled_services(cfg=mock.MagicMock())

        assert 1 == m_is_attached.call_count
        assert (
            expected_enabled_services == enabled_services_ret.enabled_services
        )
        assert expected_warnings == enabled_services_ret.warnings

    @mock.patch("uaclient.api.u.pro.status.enabled_services.v1._is_attached")
    def test_enabled_services_when_unattached(self, m_is_attached):
        m_is_attached.return_value = mock.MagicMock(is_attached=False)

        assert [] == _enabled_services(cfg=mock.MagicMock()).enabled_services
        assert 1 == m_is_attached.call_count
