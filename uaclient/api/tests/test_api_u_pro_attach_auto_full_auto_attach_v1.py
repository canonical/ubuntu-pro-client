import mock
import pytest

from uaclient import event_logger, messages
from uaclient.api import exceptions
from uaclient.api.u.pro.attach.auto.full_auto_attach.v1 import (
    FullAutoAttachOptions,
    FullAutoAttachResult,
    _enable_services_by_name,
    _full_auto_attach,
    _full_auto_attach_in_lock,
)
from uaclient.entitlements.entitlement_status import (
    CanEnableFailure,
    CanEnableFailureReason,
)
from uaclient.testing import fakes
from uaclient.testing.helpers import does_not_raise

M_PATH = "uaclient.api.u.pro.attach.auto.full_auto_attach.v1."


class TestEnableServicesByName:
    @pytest.mark.parametrize(
        [
            "services",
            "allow_beta",
            "enable_side_effect",
            "expected_enable_call_args",
            "expected_ret",
        ],
        [
            # success one service, allow beta
            (
                ["esm-infra"],
                True,
                [(True, None)],
                [
                    mock.call(
                        mock.ANY, "esm-infra", assume_yes=True, allow_beta=True
                    )
                ],
                [],
            ),
            # success multi service, no allow beta
            (
                ["esm-apps", "esm-infra", "livepatch"],
                False,
                [(True, None), (True, None), (True, None)],
                [
                    mock.call(
                        mock.ANY, "esm-apps", assume_yes=True, allow_beta=False
                    ),
                    mock.call(
                        mock.ANY,
                        "esm-infra",
                        assume_yes=True,
                        allow_beta=False,
                    ),
                    mock.call(
                        mock.ANY,
                        "livepatch",
                        assume_yes=True,
                        allow_beta=False,
                    ),
                ],
                [],
            ),
            # fail via user facing error
            (
                ["esm-apps", "esm-infra", "livepatch"],
                False,
                [
                    (True, None),
                    exceptions.EntitlementNotFoundError(
                        entitlement_name="name"
                    ),
                    fakes.FakeUbuntuProError(),
                ],
                [
                    mock.call(
                        mock.ANY, "esm-apps", assume_yes=True, allow_beta=False
                    ),
                    mock.call(
                        mock.ANY,
                        "esm-infra",
                        assume_yes=True,
                        allow_beta=False,
                    ),
                    mock.call(
                        mock.ANY,
                        "livepatch",
                        assume_yes=True,
                        allow_beta=False,
                    ),
                ],
                [
                    (
                        "esm-infra",
                        messages.E_ENTITLEMENT_NOT_FOUND.format(
                            entitlement_name="name"
                        ),
                    ),
                    ("livepatch", fakes.FakeUbuntuProError._msg),
                ],
            ),
            # fail via return
            (
                ["esm-apps", "esm-infra", "livepatch"],
                False,
                [
                    (True, None),
                    (False, None),
                    (
                        False,
                        CanEnableFailure(
                            CanEnableFailureReason.ALREADY_ENABLED,
                            messages.NamedMessage("test", "test"),
                        ),
                    ),
                ],
                [
                    mock.call(
                        mock.ANY, "esm-apps", assume_yes=True, allow_beta=False
                    ),
                    mock.call(
                        mock.ANY,
                        "esm-infra",
                        assume_yes=True,
                        allow_beta=False,
                    ),
                    mock.call(
                        mock.ANY,
                        "livepatch",
                        assume_yes=True,
                        allow_beta=False,
                    ),
                ],
                [
                    (
                        "esm-infra",
                        messages.NamedMessage("unknown", "failed to enable"),
                    ),
                    ("livepatch", messages.NamedMessage("test", "test")),
                ],
            ),
        ],
    )
    @mock.patch(M_PATH + "actions.enable_entitlement_by_name")
    def test_enable_services_by_name(
        self,
        m_enable_entitlement_by_name,
        services,
        allow_beta,
        enable_side_effect,
        expected_enable_call_args,
        expected_ret,
    ):
        m_enable_entitlement_by_name.side_effect = enable_side_effect
        ret = _enable_services_by_name(mock.MagicMock(), services, allow_beta)
        assert (
            m_enable_entitlement_by_name.call_args_list
            == expected_enable_call_args
        )
        assert ret == expected_ret


@mock.patch("uaclient.files.notices.add")
@mock.patch("uaclient.files.notices.remove")
class TestFullAutoAttachV1:
    @mock.patch("uaclient.lock.SpinLock.__enter__")
    @mock.patch(
        M_PATH + "contract.UAContractClient.update_activity_token",
    )
    @mock.patch(
        "uaclient.actions.enable_entitlement_by_name",
    )
    @mock.patch("uaclient.clouds.identity.cloud_instance_factory")
    @mock.patch("uaclient.actions.auto_attach")
    def test_error_invalid_ent_names(
        self,
        _auto_attach,
        _cloud_instance_factory,
        m_enable_ent_by_name,
        _m_update_activity_token,
        _m_lock_enter,
        _notice_remove,
        _notice_add,
        FakeConfig,
    ):
        cfg = FakeConfig()

        def enable_ent_side_effect(cfg, name, assume_yes, allow_beta):
            if name != "wrong":
                return (True, None)

            return (False, None)

        m_enable_ent_by_name.side_effect = enable_ent_side_effect
        options = FullAutoAttachOptions(
            enable=["esm-infra", "cis"],
            enable_beta=["esm-apps", "realtime-kernel", "wrong"],
        )
        with pytest.raises(exceptions.EntitlementsNotEnabledError):
            _full_auto_attach(options, cfg)

        assert 5 == m_enable_ent_by_name.call_count

    @mock.patch("uaclient.lock.SpinLock.__enter__")
    @mock.patch(
        M_PATH + "contract.UAContractClient.update_activity_token",
    )
    @mock.patch(
        "uaclient.actions.enable_entitlement_by_name",
        return_value=(False, None),
    )
    @mock.patch("uaclient.clouds.identity.cloud_instance_factory")
    @mock.patch("uaclient.actions.auto_attach")
    def test_error_full_auto_attach_fail(
        self,
        _auto_attach,
        _cloud_instance_factory,
        enable_ent_by_name,
        _m_update_activity_token,
        _m_lock_enter,
        _notice_remove,
        _notice_add,
        FakeConfig,
    ):
        cfg = FakeConfig()
        options = FullAutoAttachOptions(
            enable=["esm-infra", "fips"],
            enable_beta=["esm-apps", "ros"],
        )
        with pytest.raises(exceptions.EntitlementsNotEnabledError):
            _full_auto_attach(options, cfg)

        assert 4 == enable_ent_by_name.call_count

    @mock.patch(
        "uaclient.lock.SpinLock.__enter__",
        side_effect=[
            exceptions.LockHeldError(
                lock_request="request", lock_holder="holder", pid=10
            ),
        ],
    )
    def test_lock_held(
        self, _m_spinlock_enter, _notice_remove, _notice_read, FakeConfig
    ):
        with pytest.raises(exceptions.LockHeldError):
            _full_auto_attach(FullAutoAttachOptions, FakeConfig())

    @pytest.mark.parametrize(
        "mode",
        list(map(lambda e: e.value, event_logger.EventLoggerMode)),
    )
    @pytest.mark.parametrize(
        [
            "options",
            "is_attached",
            "is_disabled",
            "expected_auto_attach_call_args",
            "enable_services_by_name_side_effect",
            "expected_enable_services_by_name_call_args",
            "raise_expectation",
            "expect_activity_call",
            "expected_error_message",
            "expected_ret",
        ],
        [
            # already attached
            (
                FullAutoAttachOptions(),
                True,
                False,
                [],
                [],
                [],
                pytest.raises(exceptions.AlreadyAttachedError),
                False,
                messages.E_ALREADY_ATTACHED.format(
                    account_name="test_account"
                ).msg,
                None,
            ),
            # disable_auto_attach: true
            (
                FullAutoAttachOptions(),
                False,
                True,
                [],
                [],
                [],
                pytest.raises(exceptions.AutoAttachDisabledError),
                False,
                messages.E_AUTO_ATTACH_DISABLED_ERROR.msg,
                None,
            ),
            # success no options
            (
                FullAutoAttachOptions(),
                False,
                False,
                [mock.call(mock.ANY, mock.ANY, allow_enable=True)],
                [],
                [],
                does_not_raise(),
                True,
                None,
                FullAutoAttachResult(),
            ),
            # success enable
            (
                FullAutoAttachOptions(enable=["cis"]),
                False,
                False,
                [mock.call(mock.ANY, mock.ANY, allow_enable=False)],
                [[]],
                [mock.call(mock.ANY, ["cis"], allow_beta=False)],
                does_not_raise(),
                True,
                None,
                FullAutoAttachResult(),
            ),
            # success enable_beta
            (
                FullAutoAttachOptions(enable_beta=["cis"]),
                False,
                False,
                [mock.call(mock.ANY, mock.ANY, allow_enable=False)],
                [[]],
                [mock.call(mock.ANY, ["cis"], allow_beta=True)],
                does_not_raise(),
                True,
                None,
                FullAutoAttachResult(),
            ),
            # success enable and enable_beta
            (
                FullAutoAttachOptions(enable=["fips"], enable_beta=["cis"]),
                False,
                False,
                [mock.call(mock.ANY, mock.ANY, allow_enable=False)],
                [[], []],
                [
                    mock.call(mock.ANY, ["fips"], allow_beta=False),
                    mock.call(mock.ANY, ["cis"], allow_beta=True),
                ],
                does_not_raise(),
                True,
                None,
                FullAutoAttachResult(),
            ),
            # fail to enable
            (
                FullAutoAttachOptions(enable=["fips"], enable_beta=["cis"]),
                False,
                False,
                [mock.call(mock.ANY, mock.ANY, allow_enable=False)],
                [
                    [("fips", messages.NamedMessage("one", "two"))],
                    [("cis", messages.NamedMessage("three", "four"))],
                ],
                [
                    mock.call(mock.ANY, ["fips"], allow_beta=False),
                    mock.call(mock.ANY, ["cis"], allow_beta=True),
                ],
                pytest.raises(exceptions.EntitlementsNotEnabledError),
                True,
                messages.E_ENTITLEMENTS_NOT_ENABLED_ERROR.msg,
                None,
            ),
        ],
    )
    @mock.patch(
        M_PATH + "contract.UAContractClient.update_activity_token",
    )
    @mock.patch(M_PATH + "_enable_services_by_name")
    @mock.patch(M_PATH + "actions.auto_attach")
    @mock.patch(M_PATH + "identity.cloud_instance_factory")
    @mock.patch(M_PATH + "util.is_config_value_true")
    def test_full_auto_attach_v1(
        self,
        m_is_config_value_true,
        m_cloud_instance_factory,
        m_auto_attach,
        m_enable_services_by_name,
        m_update_activity_token,
        _notice_remove,
        _notice_add,
        options,
        is_attached,
        is_disabled,
        expected_auto_attach_call_args,
        enable_services_by_name_side_effect,
        expected_enable_services_by_name_call_args,
        raise_expectation,
        expect_activity_call,
        expected_error_message,
        expected_ret,
        mode,
        FakeConfig,
    ):
        if is_attached:
            cfg = FakeConfig.for_attached_machine()
        else:
            cfg = FakeConfig()
        m_is_config_value_true.return_value = is_disabled
        m_enable_services_by_name.side_effect = (
            enable_services_by_name_side_effect
        )
        with raise_expectation as e:
            ret = _full_auto_attach_in_lock(options, cfg, mode)
        assert m_auto_attach.call_args_list == expected_auto_attach_call_args
        assert (
            m_enable_services_by_name.call_args_list
            == expected_enable_services_by_name_call_args
        )
        if expected_error_message is not None:
            assert e.value.msg == expected_error_message
        if expected_ret is not None:
            assert ret == expected_ret
        if expect_activity_call:
            assert 1 == m_update_activity_token.call_count
        else:
            assert 0 == m_update_activity_token.call_count
