import contextlib
import io
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
        return_code = 1
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

        expected_msg = "ent2\n\nent3\n\n"
        expected_msg += status.action_report(
            action_name="disabled",
            entitlements_not_found=["ent1"],
            entitlements_not_succeeded=["ent2"],
            entitlements_succeeded=["ent3"],
        )

        fake_stdout = io.StringIO()
        with contextlib.redirect_stdout(fake_stdout):
            ret = action_disable(args_mock, m_cfg)

        assert expected_msg == fake_stdout.getvalue()

        for m_ent_cls in [m_ent2_cls, m_ent3_cls]:
            assert [
                mock.call(m_cfg, assume_yes=assume_yes)
            ] == m_ent_cls.call_args_list

        expected_disable_call = mock.call()
        for m_ent in [m_ent2_obj, m_ent3_obj]:
            assert [expected_disable_call] == m_ent.disable.call_args_list

        assert 0 == m_ent1_obj.call_count

        assert return_code == ret
        assert num_calls == m_cfg.status.call_count

    @pytest.mark.parametrize(
        "uid,expected_error_template", [(1000, status.MESSAGE_NONROOT_USER)]
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
    def test_invalid_servive_names(self, m_getuid, names, FakeConfig):
        m_getuid.return_value = 0

        cfg = FakeConfig.for_attached_machine()
        fake_stdout = io.StringIO()
        with contextlib.redirect_stdout(fake_stdout):
            args = mock.MagicMock()
            args.names = names
            action_disable(args, cfg)

        assert (
            status.action_report(
                action_name="disabled",
                entitlements_not_found=names,
                entitlements_not_succeeded=[],
                entitlements_succeeded=[],
            )
            == fake_stdout.getvalue()
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
