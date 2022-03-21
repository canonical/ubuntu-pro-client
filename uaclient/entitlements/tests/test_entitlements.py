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
