import mock
import pytest

from uaclient.cli import action_disable
from uaclient import exceptions
from uaclient import status


@mock.patch("uaclient.cli.os.getuid", return_value=0)
class TestDisable:
    @pytest.mark.parametrize("names", [["testitlement"], ["ent1", "ent2"]])
    @pytest.mark.parametrize("assume_yes", (True, False))
    @pytest.mark.parametrize(
        "disable_return,return_code", ((True, 0), (False, 1))
    )
    @mock.patch("uaclient.cli.entitlements")
    def test_entitlement_instantiated_and_disabled(
        self,
        m_entitlements,
        _m_getuid,
        disable_return,
        return_code,
        assume_yes,
        names,
    ):
        entitlements_cls = []
        entitlements_obj = []
        m_entitlements.ENTITLEMENT_CLASS_BY_NAME = {}
        for entitlement_name in names:
            m_entitlement_cls = mock.Mock()

            m_entitlement = m_entitlement_cls.return_value
            m_entitlement.disable.return_value = disable_return

            m_entitlements.ENTITLEMENT_CLASS_BY_NAME[
                entitlement_name
            ] = m_entitlement_cls

            entitlements_obj.append(m_entitlement)
            entitlements_cls.append(m_entitlement_cls)

        m_cfg = mock.Mock()
        args_mock = mock.Mock()
        args_mock.names = names
        args_mock.assume_yes = assume_yes

        ret = action_disable(args_mock, m_cfg)

        for m_entitlement_cls in entitlements_cls:
            assert [
                mock.call(m_cfg, assume_yes=assume_yes)
            ] == m_entitlement_cls.call_args_list

        expected_disable_call = mock.call()
        for m_entitlement in entitlements_obj:
            assert [
                expected_disable_call
            ] == m_entitlement.disable.call_args_list

        assert return_code == ret
        assert len(entitlements_cls) == m_cfg.status.call_count

    @pytest.mark.parametrize("assume_yes", (True, False))
    @mock.patch("uaclient.cli.entitlements")
    def test_entitlements_not_found_disabled_and_enabled(
        self, m_entitlements, _m_getuid, assume_yes
    ):
        expected_error_tmpl = status.MESSAGE_INVALID_SERVICE_OP_FAILURE_TMPL
        num_calls = 2

        m_ent1_cls = mock.Mock()
        m_ent1_obj = m_ent1_cls.return_value
        m_ent1_obj.disable.return_value = False

        m_ent2_cls = mock.Mock()
        m_ent2_obj = m_ent2_cls.return_value
        m_ent2_obj.disable.return_value = False

        m_ent3_cls = mock.Mock()
        m_ent3_obj = m_ent3_cls.return_value
        m_ent3_obj.disable.return_value = True

        m_entitlements.ENTITLEMENT_CLASS_BY_NAME = {
            "ent2": m_ent2_cls,
            "ent3": m_ent3_cls,
        }

        m_cfg = mock.Mock()
        args_mock = mock.Mock()
        args_mock.names = ["ent1", "ent2", "ent3"]
        args_mock.assume_yes = assume_yes

        with pytest.raises(exceptions.UserFacingError) as err:
            action_disable(args_mock, m_cfg)

        assert (
            expected_error_tmpl.format(operation="disable", name="ent1")
            == err.value.msg
        )

        for m_ent_cls in [m_ent2_cls, m_ent3_cls]:
            assert [
                mock.call(m_cfg, assume_yes=assume_yes)
            ] == m_ent_cls.call_args_list

        expected_disable_call = mock.call()
        for m_ent in [m_ent2_obj, m_ent3_obj]:
            assert [expected_disable_call] == m_ent.disable.call_args_list

        assert 0 == m_ent1_obj.call_count
        assert num_calls == m_cfg.status.call_count

    @pytest.mark.parametrize(
        "uid,expected_error_template",
        [
            (0, status.MESSAGE_INVALID_SERVICE_OP_FAILURE_TMPL),
            (1000, status.MESSAGE_NONROOT_USER),
        ],
    )
    def test_invalid_service_error_message(
        self, m_getuid, uid, expected_error_template, FakeConfig
    ):
        """Check invalid service name results in custom error message."""
        m_getuid.return_value = uid

        cfg = FakeConfig.for_attached_machine()
        with pytest.raises(exceptions.UserFacingError) as err:
            args = mock.MagicMock()
            args.names = ["bogus"]
            action_disable(args, cfg)
        assert (
            expected_error_template.format(operation="disable", name="bogus")
            == err.value.msg
        )

    @pytest.mark.parametrize("names", [["bogus"], ["bogus1", "bogus2"]])
    def test_invalid_service_names(self, m_getuid, names, FakeConfig):
        m_getuid.return_value = 0
        expected_error_tmpl = status.MESSAGE_INVALID_SERVICE_OP_FAILURE_TMPL

        cfg = FakeConfig.for_attached_machine()
        with pytest.raises(exceptions.UserFacingError) as err:
            args = mock.MagicMock()
            args.names = names
            action_disable(args, cfg)

        assert (
            expected_error_tmpl.format(
                operation="disable", name=", ".join(sorted(names))
            )
            == err.value.msg
        )

    @pytest.mark.parametrize(
        "uid,expected_error_template",
        [
            (0, status.MESSAGE_ENABLE_FAILURE_UNATTACHED_TMPL),
            (1000, status.MESSAGE_NONROOT_USER),
        ],
    )
    def test_unattached_error_message(
        self, m_getuid, uid, expected_error_template, FakeConfig
    ):
        """Check that root user gets unattached message."""
        m_getuid.return_value = uid

        cfg = FakeConfig()
        with pytest.raises(exceptions.UserFacingError) as err:
            args = mock.MagicMock()
            args.names = ["esm-infra"]
            action_disable(args, cfg)
        assert (
            expected_error_template.format(name="esm-infra") == err.value.msg
        )
