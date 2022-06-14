"""Tests related to uaclient.entitlement.__init__ module."""
import mock
import pytest

from uaclient import entitlements, exceptions


class TestValidServices:
    @pytest.mark.parametrize("show_all_names", ((True), (False)))
    @pytest.mark.parametrize("allow_beta", ((True), (False)))
    @pytest.mark.parametrize("is_beta", ((True), (False)))
    @mock.patch("uaclient.entitlements.is_config_value_true")
    def test_valid_services(
        self,
        m_is_config_value,
        show_all_names,
        allow_beta,
        is_beta,
        FakeConfig,
    ):
        m_is_config_value.return_value = allow_beta

        m_cls_1 = mock.MagicMock()
        m_inst_1 = mock.MagicMock()
        m_cls_1.is_beta = False
        m_inst_1.presentation_name = "ent1"
        m_inst_1.valid_names = ["ent1", "othername"]
        m_cls_1.return_value = m_inst_1

        m_cls_2 = mock.MagicMock()
        m_inst_2 = mock.MagicMock()
        m_cls_2.is_beta = is_beta
        m_inst_2.presentation_name = "ent2"
        m_inst_2.valid_names = ["ent2"]
        m_cls_2.return_value = m_inst_2

        ents = {m_cls_1, m_cls_2}

        with mock.patch.object(entitlements, "ENTITLEMENT_CLASSES", ents):
            expected_services = ["ent1"]
            if allow_beta or not is_beta:
                expected_services.append("ent2")
            if show_all_names:
                expected_services.append("othername")

            assert expected_services == entitlements.valid_services(
                cfg=FakeConfig(), all_names=show_all_names
            )


class TestEntitlementFactory:
    def test_entitlement_factory(self, FakeConfig):
        m_cls_1 = mock.MagicMock()
        m_cls_1.return_value.valid_names = ["ent1", "othername"]

        m_cls_2 = mock.MagicMock()
        m_cls_2.return_value.valid_names = ["ent2"]

        ents = {m_cls_1, m_cls_2}
        cfg = FakeConfig()

        with mock.patch.object(entitlements, "ENTITLEMENT_CLASSES", ents):
            assert m_cls_1 == entitlements.entitlement_factory(
                cfg=cfg, name="othername"
            )
            assert m_cls_2 == entitlements.entitlement_factory(
                cfg=cfg, name="ent2"
            )
        with pytest.raises(exceptions.EntitlementNotFoundError):
            entitlements.entitlement_factory(cfg=cfg, name="nonexistent")


class TestSortEntitlements:
    def test_disable_order(self, FakeConfig):
        m_cls_1 = mock.MagicMock()
        m_obj_1 = m_cls_1.return_value
        type(m_obj_1).dependent_services = mock.PropertyMock(return_value=())
        type(m_cls_1).name = mock.PropertyMock(return_value="ent1")

        m_cls_2 = mock.MagicMock()
        m_obj_2 = m_cls_2.return_value
        type(m_obj_2).dependent_services = mock.PropertyMock(return_value=())
        type(m_cls_2).name = mock.PropertyMock(return_value="ent2")

        m_cls_3 = mock.MagicMock()
        m_obj_3 = m_cls_3.return_value
        type(m_obj_3).dependent_services = mock.PropertyMock(
            return_value=(m_cls_1, m_cls_2)
        )
        type(m_cls_3).name = mock.PropertyMock(return_value="ent3")

        m_cls_5 = mock.MagicMock()
        m_obj_5 = m_cls_5.return_value
        type(m_obj_5).dependent_services = mock.PropertyMock(return_value=())
        type(m_cls_5).name = mock.PropertyMock(return_value="ent5")

        m_cls_6 = mock.MagicMock()
        m_obj_6 = m_cls_6.return_value
        type(m_obj_6).dependent_services = mock.PropertyMock(return_value=())
        type(m_cls_6).name = mock.PropertyMock(return_value="ent6")

        m_cls_4 = mock.MagicMock()
        m_obj_4 = m_cls_4.return_value
        type(m_obj_4).dependent_services = mock.PropertyMock(
            return_value=(m_cls_5, m_cls_6)
        )
        type(m_cls_4).name = mock.PropertyMock(return_value="ent4")

        m_entitlements = [
            m_cls_1,
            m_cls_2,
            m_cls_3,
            m_cls_4,
            m_cls_5,
            m_cls_6,
        ]

        with mock.patch.object(
            entitlements, "ENTITLEMENT_CLASSES", m_entitlements
        ):
            assert [
                "ent1",
                "ent2",
                "ent3",
                "ent5",
                "ent6",
                "ent4",
            ] == entitlements.entitlements_disable_order(FakeConfig())

    def test_enable_order(self, FakeConfig):
        m_cls_2 = mock.MagicMock()
        m_obj_2 = m_cls_2.return_value
        type(m_obj_2).required_services = mock.PropertyMock(return_value=())
        type(m_cls_2).name = mock.PropertyMock(return_value="ent2")

        m_cls_1 = mock.MagicMock()
        m_obj_1 = m_cls_1.return_value
        type(m_obj_1).required_services = mock.PropertyMock(
            return_value=(m_cls_2,)
        )
        type(m_cls_1).name = mock.PropertyMock(return_value="ent1")

        m_cls_3 = mock.MagicMock()
        m_obj_3 = m_cls_3.return_value
        type(m_obj_3).required_services = mock.PropertyMock(
            return_value=(m_cls_1, m_cls_2)
        )
        type(m_cls_3).name = mock.PropertyMock(return_value="ent3")

        m_cls_5 = mock.MagicMock()
        m_obj_5 = m_cls_5.return_value
        type(m_obj_5).required_services = mock.PropertyMock(return_value=())
        type(m_cls_5).name = mock.PropertyMock(return_value="ent5")

        m_cls_6 = mock.MagicMock()
        m_obj_6 = m_cls_6.return_value
        type(m_obj_6).required_services = mock.PropertyMock(return_value=())
        type(m_cls_6).name = mock.PropertyMock(return_value="ent6")

        m_cls_4 = mock.MagicMock()
        m_obj_4 = m_cls_4.return_value
        type(m_obj_4).required_services = mock.PropertyMock(
            return_value=(m_cls_5, m_cls_6)
        )
        type(m_cls_4).name = mock.PropertyMock(return_value="ent4")

        m_entitlements = [
            m_cls_1,
            m_cls_2,
            m_cls_3,
            m_cls_4,
            m_cls_5,
            m_cls_6,
        ]

        with mock.patch.object(
            entitlements, "ENTITLEMENT_CLASSES", m_entitlements
        ):
            assert [
                "ent2",
                "ent1",
                "ent3",
                "ent5",
                "ent6",
                "ent4",
            ] == entitlements.entitlements_enable_order(cfg=FakeConfig())
