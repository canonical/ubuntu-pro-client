import contextlib
import io
import json
import textwrap

import mock
import pytest

from uaclient import entitlements, event_logger, exceptions, lock, messages
from uaclient.api.u.pro.services.dependencies.v1 import (
    ServiceWithDependencies,
    ServiceWithReason,
)
from uaclient.cli import main_error_handler
from uaclient.cli.disable import (
    disable_command,
    prompt_for_dependency_handling,
)
from uaclient.entitlements.entitlement_status import (
    CanDisableFailure,
    CanDisableFailureReason,
)
from uaclient.testing.helpers import does_not_raise


@pytest.fixture
def all_service_msg(FakeConfig):
    ALL_SERVICE_MSG = "\n".join(
        textwrap.wrap(
            "Try "
            + ", ".join(entitlements.valid_services(cfg=FakeConfig()))
            + ".",
            width=80,
            break_long_words=False,
            break_on_hyphens=False,
        )
    )
    return ALL_SERVICE_MSG


class TestDisable:
    @pytest.mark.parametrize("service", [["testitlement"], ["ent1", "ent2"]])
    @pytest.mark.parametrize("assume_yes", (True, False))
    @pytest.mark.parametrize(
        "disable_return,return_code", ((True, 0), (False, 1))
    )
    @mock.patch("uaclient.cli.disable._enabled_services")
    @mock.patch("uaclient.lock.check_lock_info", return_value=(-1, ""))
    @mock.patch(
        "uaclient.cli.contract.UAContractClient.update_activity_token",
    )
    @mock.patch("uaclient.cli.entitlements.entitlement_factory")
    @mock.patch("uaclient.cli.entitlements.valid_services")
    @mock.patch("uaclient.status.status")
    def test_entitlement_instantiated_and_disabled(
        self,
        m_status,
        m_valid_services,
        m_entitlement_factory,
        m_update_activity_token,
        _m_check_lock_info,
        m_enabled_services,
        disable_return,
        return_code,
        assume_yes,
        service,
        tmpdir,
        capsys,
        event,
        FakeConfig,
        fake_machine_token_file,
    ):
        entitlements_obj = []
        ent_dict = {}
        m_valid_services.return_value = []

        if not disable_return:
            fail = CanDisableFailure(
                CanDisableFailureReason.ALREADY_DISABLED,
                message=messages.NamedMessage("test-code", "test"),
            )
        else:
            fail = None

        for entitlement_name in service:
            m_entitlement = mock.MagicMock()
            m_entitlement._check_for_reboot.return_value = False
            m_entitlement.enabled_variant = None
            m_entitlement.disable.return_value = (disable_return, fail)

            entitlements_obj.append(m_entitlement)
            m_valid_services.return_value.append(entitlement_name)
            type(m_entitlement).name = mock.PropertyMock(
                return_value=entitlement_name
            )
            ent_dict[entitlement_name] = m_entitlement

        m_enabled_services.return_value = mock.MagicMock(
            enabled_services=ent_dict.values()
        )

        def factory_side_effect(cfg, name, **kwargs):
            return ent_dict.get(name, mock.MagicMock())

        m_entitlement_factory.side_effect = factory_side_effect

        cfg = FakeConfig()
        fake_machine_token_file.attached = True
        args_mock = mock.Mock()
        args_mock.service = service
        args_mock.assume_yes = assume_yes
        args_mock.purge = False

        with mock.patch.object(lock, "lock_data_file"):
            ret = disable_command.action(args_mock, cfg=cfg)

        expected_disable_call = mock.call(mock.ANY)
        for m_entitlement in entitlements_obj:
            assert [
                expected_disable_call
            ] == m_entitlement.disable.call_args_list

        assert return_code == ret
        assert len(entitlements_obj) == m_status.call_count
        assert 1 == m_update_activity_token.call_count

        cfg = FakeConfig()
        args_mock.assume_yes = True
        args_mock.format = "json"
        with mock.patch.object(
            event, "_event_logger_mode", event_logger.EventLoggerMode.JSON
        ):
            with mock.patch.object(event, "set_event_mode"):
                with mock.patch.object(lock, "lock_data_file"):
                    fake_stdout = io.StringIO()
                    with contextlib.redirect_stdout(fake_stdout):
                        ret = disable_command.action(args_mock, cfg=cfg)

        expected = {
            "_schema_version": event_logger.JSON_SCHEMA_VERSION,
            "result": "success" if disable_return else "failure",
            "errors": [],
            "failed_services": [] if disable_return else service,
            "needs_reboot": False,
            "processed_services": service if disable_return else [],
            "warnings": [],
        }

        if not disable_return:
            expected["errors"] = [
                {
                    "message": "test",
                    "message_code": "test-code",
                    "service": ent_name,
                    "type": "service",
                }
                for ent_name in service
            ]

        assert return_code == ret
        assert expected == json.loads(fake_stdout.getvalue())

    @pytest.mark.parametrize("assume_yes", (True, False))
    @mock.patch("uaclient.cli.disable._enabled_services")
    @mock.patch("uaclient.contract.UAContractClient.update_activity_token")
    @mock.patch("uaclient.lock.check_lock_info", return_value=(-1, ""))
    @mock.patch("uaclient.entitlements.entitlement_factory")
    @mock.patch("uaclient.entitlements.valid_services")
    @mock.patch("uaclient.status.status")
    def test_entitlements_not_found_disabled_and_enabled(
        self,
        m_status,
        m_valid_services,
        m_entitlement_factory,
        _m_check_lock_info,
        _m_update_activity_token,
        m_enabled_services,
        assume_yes,
        tmpdir,
        event,
        FakeConfig,
        fake_machine_token_file,
    ):
        expected_error_tmpl = messages.E_INVALID_SERVICE_OP_FAILURE
        num_calls = 2

        m_ent1_obj = mock.MagicMock()
        m_ent1_obj.enabled_variant = None
        m_ent1_obj.disable.return_value = (
            False,
            CanDisableFailure(
                CanDisableFailureReason.ALREADY_DISABLED,
                message=messages.NamedMessage("test-code", "test"),
            ),
        )
        type(m_ent1_obj).name = mock.PropertyMock(return_value="ent1")
        m_ent1_obj._check_for_reboot.return_value = False

        m_ent2_obj = mock.MagicMock()
        m_ent2_obj.enabled_variant = None
        m_ent2_obj.disable.return_value = (
            False,
            CanDisableFailure(
                CanDisableFailureReason.ALREADY_DISABLED,
                message=messages.NamedMessage("test-code2", "test2"),
            ),
        )
        type(m_ent2_obj).name = mock.PropertyMock(return_value="ent2")
        m_ent2_obj._check_for_reboot.return_value = False

        m_ent3_cls = mock.MagicMock()
        m_ent3_obj = m_ent3_cls.return_value
        m_ent3_obj.enabled_variant = None
        m_ent3_obj.disable.return_value = (True, None)
        type(m_ent3_obj).name = mock.PropertyMock(return_value="ent3")
        m_ent3_obj._check_for_reboot.return_value = False

        def factory_side_effect(cfg, name, **kwargs):
            if name == "ent2":
                return m_ent2_obj
            if name == "ent3":
                return m_ent3_obj
            return mock.MagicMock()

        m_entitlement_factory.side_effect = factory_side_effect
        m_valid_services.return_value = ["ent2", "ent3"]
        m_enabled_services.return_value = mock.MagicMock(
            enabled_service=[m_ent1_obj, m_ent2_obj, m_ent3_obj]
        )

        cfg = FakeConfig()
        fake_machine_token_file.attached = True
        args_mock = mock.Mock()
        args_mock.service = ["ent1", "ent2", "ent3"]
        args_mock.assume_yes = assume_yes
        args_mock.purge = False

        first_fake_stdout = io.StringIO()
        with contextlib.redirect_stdout(first_fake_stdout):
            with mock.patch.object(lock, "lock_data_file"):
                disable_command.action(args_mock, cfg=cfg)

        assert (
            expected_error_tmpl.format(
                operation="disable",
                invalid_service="ent1",
                service_msg="Try ent2, ent3.",
            ).msg
            in first_fake_stdout.getvalue()
        )

        expected_disable_call = mock.call(mock.ANY)
        for m_ent in [m_ent2_obj, m_ent3_obj]:
            assert [expected_disable_call] == m_ent.disable.call_args_list

        assert 0 == m_ent1_obj.call_count
        assert num_calls == m_status.call_count

        args_mock.assume_yes = True
        args_mock.format = "json"
        with mock.patch.object(lock, "lock_data_file"):
            fake_stdout = io.StringIO()
            with contextlib.redirect_stdout(fake_stdout):
                main_error_handler(disable_command.action)(args_mock, cfg=cfg)

        expected = {
            "_schema_version": event_logger.JSON_SCHEMA_VERSION,
            "result": "failure",
            "errors": [
                {
                    "message": "test2",
                    "message_code": "test-code2",
                    "service": "ent2",
                    "type": "service",
                },
                {
                    "additional_info": {
                        "invalid_service": "ent1",
                        "operation": "disable",
                        "service_msg": "Try ent2, ent3.",
                    },
                    "message": (
                        "Cannot disable unknown service 'ent1'.\n"
                        "Try ent2, ent3."
                    ),
                    "message_code": "invalid-service-or-failure",
                    "service": None,
                    "type": "system",
                },
            ],
            "failed_services": ["ent2"],
            "needs_reboot": False,
            "processed_services": ["ent3"],
            "warnings": [],
        }

        assert expected == json.loads(fake_stdout.getvalue())

    @pytest.mark.parametrize(
        "root,expected_error_template",
        [
            (False, messages.E_NONROOT_USER),
        ],
    )
    @mock.patch("uaclient.contract.UAContractClient.update_activity_token")
    @mock.patch("uaclient.lock.check_lock_info", return_value=(-1, ""))
    @mock.patch("uaclient.util.we_are_currently_root")
    def test_invalid_service_error_message(
        self,
        m_we_are_currently_root,
        _m_check_lock_info,
        _m_update_activity_token,
        root,
        expected_error_template,
        FakeConfig,
        fake_machine_token_file,
        event,
        all_service_msg,
    ):
        """Check invalid service name results in custom error message."""
        m_we_are_currently_root.return_value = root
        fake_machine_token_file.attached = True

        cfg = FakeConfig()
        args = mock.MagicMock()
        args.purge = False
        args.service = ["esm-infra"]

        expected_error = expected_error_template
        expected_info = None

        with pytest.raises(exceptions.UbuntuProError) as err:
            with mock.patch.object(lock, "lock_data_file"):
                disable_command.action(args, cfg)

        assert expected_error.msg == err.value.msg

        args.assume_yes = True
        args.format = "json"
        with pytest.raises(SystemExit):
            with mock.patch.object(
                event, "_event_logger_mode", event_logger.EventLoggerMode.JSON
            ):
                with mock.patch.object(event, "set_event_mode"):
                    fake_stdout = io.StringIO()
                    with contextlib.redirect_stdout(fake_stdout):
                        with mock.patch.object(lock, "lock_data_file"):
                            main_error_handler(disable_command.action)(
                                args, cfg
                            )

        expected = {
            "_schema_version": event_logger.JSON_SCHEMA_VERSION,
            "result": "failure",
            "errors": [
                {
                    "message": expected_error.msg,
                    "message_code": expected_error.name,
                    "service": None,
                    "type": "system",
                }
            ],
            "failed_services": [],
            "needs_reboot": False,
            "processed_services": [],
            "warnings": [],
        }
        if expected_info is not None:
            expected["errors"][0]["additional_info"] = expected_info
        assert expected == json.loads(fake_stdout.getvalue())

    @pytest.mark.parametrize("service", [["bogus"], ["bogus1", "bogus2"]])
    @mock.patch("uaclient.contract.UAContractClient.update_activity_token")
    @mock.patch("uaclient.lock.check_lock_info", return_value=(-1, ""))
    def test_invalid_service_names(
        self,
        _m_check_lock_info,
        _m_update_activity_token,
        service,
        FakeConfig,
        fake_machine_token_file,
        event,
        all_service_msg,
    ):
        expected_error_tmpl = messages.E_INVALID_SERVICE_OP_FAILURE

        cfg = FakeConfig()
        fake_machine_token_file.attached = True
        args = mock.MagicMock()
        args.purge = False
        expected_error = expected_error_tmpl.format(
            operation="disable",
            invalid_service=", ".join(sorted(service)),
            service_msg=all_service_msg,
        )
        first_fake_stdout = io.StringIO()
        with contextlib.redirect_stdout(first_fake_stdout):
            with mock.patch.object(lock, "lock_data_file"):
                args.service = service
                disable_command.action(args, cfg)

        assert expected_error.msg in first_fake_stdout.getvalue()

        args.assume_yes = True
        args.format = "json"
        with mock.patch.object(lock, "lock_data_file"):
            fake_stdout = io.StringIO()
            with contextlib.redirect_stdout(fake_stdout):
                main_error_handler(disable_command.action)(args, cfg)

        expected = {
            "_schema_version": event_logger.JSON_SCHEMA_VERSION,
            "result": "failure",
            "errors": [
                {
                    "additional_info": {
                        "invalid_service": ", ".join(sorted(service)),
                        "operation": "disable",
                        "service_msg": all_service_msg,
                    },
                    "message": expected_error.msg,
                    "message_code": expected_error.name,
                    "service": None,
                    "type": "system",
                }
            ],
            "failed_services": [],
            "needs_reboot": False,
            "processed_services": [],
            "warnings": [],
        }
        assert expected == json.loads(fake_stdout.getvalue())

    @pytest.mark.parametrize(
        "root,expected_error_template",
        [
            (True, messages.E_VALID_SERVICE_FAILURE_UNATTACHED),
            (False, messages.E_NONROOT_USER),
        ],
    )
    @mock.patch("uaclient.util.we_are_currently_root")
    def test_unattached_error_message(
        self,
        m_we_are_currently_root,
        root,
        expected_error_template,
        FakeConfig,
        event,
    ):
        """Check that root user gets unattached message."""
        m_we_are_currently_root.return_value = root

        cfg = FakeConfig()
        args = mock.MagicMock()
        args.command = "disable"
        if root:
            expected_error = expected_error_template.format(
                valid_service="esm-infra", operation="disable"
            )
            expected_info = {
                "valid_service": "esm-infra",
                "operation": "disable",
            }
        else:
            expected_error = expected_error_template
            expected_info = None

        with pytest.raises(exceptions.UbuntuProError) as err:
            args.service = ["esm-infra"]
            disable_command.action(args, cfg)

        assert expected_error.msg == err.value.msg

        args.assume_yes = True
        args.format = "json"
        with pytest.raises(SystemExit):
            with mock.patch.object(
                event, "_event_logger_mode", event_logger.EventLoggerMode.JSON
            ):
                with mock.patch.object(event, "set_event_mode"):
                    fake_stdout = io.StringIO()
                    with contextlib.redirect_stdout(fake_stdout):
                        main_error_handler(disable_command.action)(args, cfg)

        expected = {
            "_schema_version": event_logger.JSON_SCHEMA_VERSION,
            "result": "failure",
            "errors": [
                {
                    "message": expected_error.msg,
                    "message_code": expected_error.name,
                    "service": None,
                    "type": "system",
                }
            ],
            "failed_services": [],
            "needs_reboot": False,
            "processed_services": [],
            "warnings": [],
        }
        if expected_info is not None:
            expected["errors"][0]["additional_info"] = expected_info
        assert expected == json.loads(fake_stdout.getvalue())

    @mock.patch("uaclient.lock.check_lock_info")
    @mock.patch("time.sleep")
    @mock.patch("uaclient.system.subp")
    def test_lock_file_exists(
        self,
        m_subp,
        m_sleep,
        m_check_lock_info,
        FakeConfig,
        fake_machine_token_file,
        event,
    ):
        """Check inability to disable if operation in progress holds lock."""
        cfg = FakeConfig()
        fake_machine_token_file.attached = True
        args = mock.MagicMock()
        expected_error = messages.E_LOCK_HELD_ERROR.format(
            lock_request="pro disable", lock_holder="pro enable", pid="123"
        )
        m_check_lock_info.return_value = (123, "pro enable")
        with pytest.raises(exceptions.LockHeldError) as err:
            args.service = ["esm-infra"]
            disable_command.action(args, cfg)
        assert 12 == m_check_lock_info.call_count
        assert expected_error.msg == err.value.msg

        args.assume_yes = True
        args.format = "json"
        with pytest.raises(SystemExit):
            with mock.patch.object(
                event, "_event_logger_mode", event_logger.EventLoggerMode.JSON
            ):
                with mock.patch.object(event, "set_event_mode"):
                    fake_stdout = io.StringIO()
                    with contextlib.redirect_stdout(fake_stdout):
                        main_error_handler(disable_command.action)(args, cfg)

        expected = {
            "_schema_version": event_logger.JSON_SCHEMA_VERSION,
            "result": "failure",
            "errors": [
                {
                    "additional_info": {
                        "lock_holder": "pro enable",
                        "lock_request": "pro disable",
                        "pid": 123,
                    },
                    "message": expected_error.msg,
                    "message_code": expected_error.name,
                    "service": None,
                    "type": "system",
                }
            ],
            "failed_services": [],
            "needs_reboot": False,
            "processed_services": [],
            "warnings": [],
        }
        assert expected == json.loads(fake_stdout.getvalue())

    def test_format_json_fails_when_assume_yes_flag_not_used(self, event):
        cfg = mock.MagicMock()
        args_mock = mock.MagicMock()
        args_mock.format = "json"
        args_mock.assume_yes = False

        with pytest.raises(SystemExit):
            with mock.patch.object(
                event, "_event_logger_mode", event_logger.EventLoggerMode.JSON
            ):
                fake_stdout = io.StringIO()
                with contextlib.redirect_stdout(fake_stdout):
                    main_error_handler(disable_command.action)(args_mock, cfg)

        expected_message = messages.E_JSON_FORMAT_REQUIRE_ASSUME_YES
        expected = {
            "_schema_version": event_logger.JSON_SCHEMA_VERSION,
            "result": "failure",
            "errors": [
                {
                    "message": expected_message.msg,
                    "message_code": expected_message.name,
                    "service": None,
                    "type": "system",
                }
            ],
            "failed_services": [],
            "needs_reboot": False,
            "processed_services": [],
            "warnings": [],
        }
        assert expected == json.loads(fake_stdout.getvalue())

    @mock.patch("uaclient.lock.check_lock_info", return_value=(-1, ""))
    @mock.patch("uaclient.cli.cli_util._is_attached")
    def test_purge_assume_yes_incompatible(
        self, m_is_attached, _m_check_lock_info, capsys
    ):
        cfg = mock.MagicMock()
        args_mock = mock.MagicMock()
        args_mock.service = "test"
        args_mock.assume_yes = True
        args_mock.purge = True

        m_is_attached.return_value = mock.MagicMock(
            is_attached=True,
            contract_status="active",
            contract_remaining_days=100,
        )

        with pytest.raises(SystemExit):
            with mock.patch.object(lock, "lock_data_file"):
                main_error_handler(disable_command.action)(args_mock, cfg)

        _out, err = capsys.readouterr()

        assert (
            messages.E_INVALID_OPTION_COMBINATION.format(
                option1="--purge", option2="--assume-yes"
            ).msg
            in err.strip()
        )


class TestPromptForDependencyHandling:
    @pytest.mark.parametrize(
        [
            "service",
            "all_dependencies",
            "enabled_service_names",
            "called_name",
            "service_title",
            "prompt_side_effects",
            "expected_prompts",
            "expected_raise",
        ],
        [
            # no dependencies
            (
                "one",
                [
                    ServiceWithDependencies(
                        name="two", incompatible_with=[], depends_on=[]
                    )
                ],
                [],
                "one",
                "One",
                [],
                [],
                does_not_raise(),
            ),
            # required by "two", but two not enabled
            (
                "one",
                [
                    ServiceWithDependencies(
                        name="two",
                        incompatible_with=[],
                        depends_on=[
                            ServiceWithReason(
                                name="one", reason=mock.MagicMock()
                            )
                        ],
                    )
                ],
                [],
                "one",
                "One",
                [],
                [],
                does_not_raise(),
            ),
            # required by "two", two enabled, successful prompt
            (
                "one",
                [
                    ServiceWithDependencies(
                        name="two",
                        incompatible_with=[],
                        depends_on=[
                            ServiceWithReason(
                                name="one", reason=mock.MagicMock()
                            )
                        ],
                    )
                ],
                ["two"],
                "one",
                "One",
                [True],
                [mock.call(msg=mock.ANY)],
                does_not_raise(),
            ),
            # required by "two", two enabled, denied prompt
            (
                "one",
                [
                    ServiceWithDependencies(
                        name="two",
                        incompatible_with=[],
                        depends_on=[
                            ServiceWithReason(
                                name="one", reason=mock.MagicMock()
                            )
                        ],
                    )
                ],
                ["two"],
                "one",
                "One",
                [False],
                [mock.call(msg=mock.ANY)],
                pytest.raises(exceptions.DependentServiceStopsDisable),
            ),
            # required by "two" and "three", three enabled, success
            (
                "one",
                [
                    ServiceWithDependencies(
                        name="two",
                        incompatible_with=[],
                        depends_on=[
                            ServiceWithReason(
                                name="one", reason=mock.MagicMock()
                            )
                        ],
                    ),
                    ServiceWithDependencies(
                        name="three",
                        incompatible_with=[],
                        depends_on=[
                            ServiceWithReason(
                                name="one", reason=mock.MagicMock()
                            )
                        ],
                    ),
                ],
                ["three"],
                "one",
                "One",
                [True],
                [mock.call(msg=mock.ANY)],
                does_not_raise(),
            ),
        ],
    )
    @mock.patch("uaclient.entitlements.get_title")
    @mock.patch("uaclient.util.prompt_for_confirmation")
    def test_prompt_for_dependency_handling(
        self,
        m_prompt_for_confirmation,
        m_entitlement_get_title,
        service,
        all_dependencies,
        enabled_service_names,
        called_name,
        service_title,
        prompt_side_effects,
        expected_prompts,
        expected_raise,
        FakeConfig,
    ):
        m_entitlement_get_title.side_effect = (
            lambda cfg, name, variant="": name.title()
        )
        m_prompt_for_confirmation.side_effect = prompt_side_effects

        with expected_raise:
            prompt_for_dependency_handling(
                FakeConfig(),
                service,
                all_dependencies,
                enabled_service_names,
                called_name,
                service_title,
            )

        assert expected_prompts == m_prompt_for_confirmation.call_args_list
