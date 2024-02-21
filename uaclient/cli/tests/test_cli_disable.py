import contextlib
import io
import json
import textwrap

import mock
import pytest

from uaclient import entitlements, event_logger, exceptions, messages
from uaclient.cli import action_disable, main, main_error_handler
from uaclient.entitlements.entitlement_status import (
    CanDisableFailure,
    CanDisableFailureReason,
)


@pytest.fixture
def all_service_msg(FakeConfig):
    ALL_SERVICE_MSG = "\n".join(
        textwrap.wrap(
            "Try "
            + ", ".join(
                entitlements.valid_services(cfg=FakeConfig(), allow_beta=True)
            )
            + ".",
            width=80,
            break_long_words=False,
            break_on_hyphens=False,
        )
    )
    return ALL_SERVICE_MSG


HELP_OUTPUT = textwrap.dedent(
    """\
usage: pro disable <service> [<service>] [flags]

Disable an Ubuntu Pro service.

Arguments:
  service              the name(s) of the Ubuntu Pro services to disable. One
                       of: anbox-cloud, cc-eal, cis, esm-apps, esm-infra,
                       fips, fips-preview, fips-updates, landscape, livepatch,
                       realtime-kernel, ros, ros-updates

Flags:
  -h, --help           show this help message and exit
  --assume-yes         do not prompt for confirmation before performing the
                       disable
  --format {cli,json}  output in the specified format (default: cli)
  --purge              disable the service and remove/downgrade related
                       packages (experimental)
"""
)


class TestDisable:
    @mock.patch("uaclient.cli.setup_logging")
    @mock.patch("uaclient.cli.contract.get_available_resources")
    def test_disable_help(
        self, _m_resources, _m_setup_logging, capsys, FakeConfig
    ):
        with pytest.raises(SystemExit):
            with mock.patch("sys.argv", ["/usr/bin/ua", "disable", "--help"]):
                with mock.patch(
                    "uaclient.config.UAConfig",
                    return_value=FakeConfig(),
                ):
                    main()
        out, _err = capsys.readouterr()
        assert HELP_OUTPUT == out

    @pytest.mark.parametrize("service", [["testitlement"], ["ent1", "ent2"]])
    @pytest.mark.parametrize("assume_yes", (True, False))
    @pytest.mark.parametrize(
        "disable_return,return_code", ((True, 0), (False, 1))
    )
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
        disable_return,
        return_code,
        assume_yes,
        service,
        tmpdir,
        capsys,
        event,
        FakeConfig,
    ):
        entitlements_cls = []
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
            m_entitlement_cls = mock.Mock()

            m_entitlement = m_entitlement_cls.return_value
            m_entitlement.enabled_variant = None
            m_entitlement.disable.return_value = (disable_return, fail)

            entitlements_obj.append(m_entitlement)
            entitlements_cls.append(m_entitlement_cls)
            m_valid_services.return_value.append(entitlement_name)
            ent_dict[entitlement_name] = m_entitlement_cls
            type(m_entitlement).name = mock.PropertyMock(
                return_value=entitlement_name
            )

        def factory_side_effect(cfg, name, ent_dict=ent_dict):
            return ent_dict.get(name)

        m_entitlement_factory.side_effect = factory_side_effect

        cfg = FakeConfig.for_attached_machine()
        args_mock = mock.Mock()
        args_mock.service = service
        args_mock.assume_yes = assume_yes
        args_mock.purge = False

        with mock.patch.object(cfg, "check_lock_info", return_value=(-1, "")):
            ret = action_disable(args_mock, cfg=cfg)

        for m_entitlement_cls in entitlements_cls:
            assert [
                mock.call(cfg, assume_yes=assume_yes, purge=False)
            ] == m_entitlement_cls.call_args_list

        expected_disable_call = mock.call()
        for m_entitlement in entitlements_obj:
            assert [
                expected_disable_call
            ] == m_entitlement.disable.call_args_list

        assert return_code == ret
        assert len(entitlements_cls) == m_status.call_count
        assert 1 == m_update_activity_token.call_count

        cfg = FakeConfig.for_attached_machine()
        args_mock.assume_yes = True
        args_mock.format = "json"
        with mock.patch.object(
            event, "_event_logger_mode", event_logger.EventLoggerMode.JSON
        ):
            with mock.patch.object(event, "set_event_mode"):
                with mock.patch.object(
                    cfg, "check_lock_info", return_value=(-1, "")
                ):
                    fake_stdout = io.StringIO()
                    with contextlib.redirect_stdout(fake_stdout):
                        ret = action_disable(args_mock, cfg=cfg)

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
    @mock.patch("uaclient.entitlements.entitlement_factory")
    @mock.patch("uaclient.entitlements.valid_services")
    @mock.patch("uaclient.status.status")
    def test_entitlements_not_found_disabled_and_enabled(
        self,
        m_status,
        m_valid_services,
        m_entitlement_factory,
        assume_yes,
        tmpdir,
        event,
        FakeConfig,
    ):
        expected_error_tmpl = messages.E_INVALID_SERVICE_OP_FAILURE
        num_calls = 2

        m_ent1_cls = mock.Mock()
        m_ent1_obj = m_ent1_cls.return_value
        m_ent1_obj.enabled_variant = None
        m_ent1_obj.disable.return_value = (
            False,
            CanDisableFailure(
                CanDisableFailureReason.ALREADY_DISABLED,
                message=messages.NamedMessage("test-code", "test"),
            ),
        )
        type(m_ent1_obj).name = mock.PropertyMock(return_value="ent1")

        m_ent2_cls = mock.Mock()
        m_ent2_obj = m_ent2_cls.return_value
        m_ent2_obj.enabled_variant = None
        m_ent2_obj.disable.return_value = (
            False,
            CanDisableFailure(
                CanDisableFailureReason.ALREADY_DISABLED,
                message=messages.NamedMessage("test-code2", "test2"),
            ),
        )
        type(m_ent2_obj).name = mock.PropertyMock(return_value="ent2")

        m_ent3_cls = mock.Mock()
        m_ent3_obj = m_ent3_cls.return_value
        m_ent3_obj.enabled_variant = None
        m_ent3_obj.disable.return_value = (True, None)
        type(m_ent3_obj).name = mock.PropertyMock(return_value="ent3")

        def factory_side_effect(cfg, name):
            if name == "ent2":
                return m_ent2_cls
            if name == "ent3":
                return m_ent3_cls
            return None

        m_entitlement_factory.side_effect = factory_side_effect
        m_valid_services.return_value = ["ent2", "ent3"]

        cfg = FakeConfig.for_attached_machine()
        args_mock = mock.Mock()
        args_mock.service = ["ent1", "ent2", "ent3"]
        args_mock.assume_yes = assume_yes
        args_mock.purge = False

        with pytest.raises(exceptions.UbuntuProError) as err:
            with mock.patch.object(
                cfg, "check_lock_info", return_value=(-1, "")
            ):
                action_disable(args_mock, cfg=cfg)

        assert (
            expected_error_tmpl.format(
                operation="disable",
                invalid_service="ent1",
                service_msg="Try ent2, ent3.",
            ).msg
            == err.value.msg
        )

        for m_ent_cls in [m_ent2_cls, m_ent3_cls]:
            assert [
                mock.call(cfg, assume_yes=assume_yes, purge=False)
            ] == m_ent_cls.call_args_list

        expected_disable_call = mock.call()
        for m_ent in [m_ent2_obj, m_ent3_obj]:
            assert [expected_disable_call] == m_ent.disable.call_args_list

        assert 0 == m_ent1_obj.call_count
        assert num_calls == m_status.call_count

        cfg = FakeConfig.for_attached_machine()
        args_mock.assume_yes = True
        args_mock.format = "json"
        with pytest.raises(SystemExit):
            with mock.patch.object(
                event, "_event_logger_mode", event_logger.EventLoggerMode.JSON
            ):
                with mock.patch.object(event, "set_event_mode"):
                    with mock.patch.object(
                        cfg, "check_lock_info", return_value=(-1, "")
                    ):
                        fake_stdout = io.StringIO()
                        with contextlib.redirect_stdout(fake_stdout):
                            main_error_handler(action_disable)(
                                args_mock, cfg=cfg
                            )

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
            (True, messages.E_INVALID_SERVICE_OP_FAILURE),
            (False, messages.E_NONROOT_USER),
        ],
    )
    @mock.patch("uaclient.util.we_are_currently_root")
    def test_invalid_service_error_message(
        self,
        m_we_are_currently_root,
        root,
        expected_error_template,
        FakeConfig,
        event,
        all_service_msg,
    ):
        """Check invalid service name results in custom error message."""
        m_we_are_currently_root.return_value = root

        cfg = FakeConfig.for_attached_machine()
        args = mock.MagicMock()
        args.purge = False

        if root:
            expected_error = expected_error_template.format(
                operation="disable",
                invalid_service="bogus",
                service_msg=all_service_msg,
            )
            expected_info = {
                "operation": "disable",
                "invalid_service": "bogus",
                "service_msg": all_service_msg,
            }
        else:
            expected_error = expected_error_template
            expected_info = None

        with pytest.raises(exceptions.UbuntuProError) as err:
            args.service = ["bogus"]
            action_disable(args, cfg)
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
                        main_error_handler(action_disable)(args, cfg)

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
    def test_invalid_service_names(
        self,
        service,
        FakeConfig,
        event,
        all_service_msg,
    ):
        expected_error_tmpl = messages.E_INVALID_SERVICE_OP_FAILURE

        cfg = FakeConfig.for_attached_machine()
        args = mock.MagicMock()
        args.purge = False
        expected_error = expected_error_tmpl.format(
            operation="disable",
            invalid_service=", ".join(sorted(service)),
            service_msg=all_service_msg,
        )
        with pytest.raises(exceptions.UbuntuProError) as err:
            args.service = service
            action_disable(args, cfg)

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
                        main_error_handler(action_disable)(args, cfg)

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
                valid_service="esm-infra"
            )
            expected_info = {"valid_service": "esm-infra"}
        else:
            expected_error = expected_error_template
            expected_info = None

        with pytest.raises(exceptions.UbuntuProError) as err:
            args.service = ["esm-infra"]
            action_disable(args, cfg)

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
                        main_error_handler(action_disable)(args, cfg)

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

    @mock.patch("time.sleep")
    @mock.patch("uaclient.system.subp")
    def test_lock_file_exists(
        self,
        m_subp,
        m_sleep,
        FakeConfig,
        event,
    ):
        """Check inability to disable if operation in progress holds lock."""
        cfg = FakeConfig().for_attached_machine()
        args = mock.MagicMock()
        expected_error = messages.E_LOCK_HELD_ERROR.format(
            lock_request="pro disable", lock_holder="pro enable", pid="123"
        )
        cfg.write_cache("lock", "123:pro enable")
        with pytest.raises(exceptions.LockHeldError) as err:
            args.service = ["esm-infra"]
            action_disable(args, cfg)
        assert [mock.call(["ps", "123"])] * 12 == m_subp.call_args_list
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
                        main_error_handler(action_disable)(args, cfg)

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
                    main_error_handler(action_disable)(args_mock, cfg)

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

    @mock.patch("uaclient.cli.cli_util._is_attached")
    def test_purge_assume_yes_incompatible(self, m_is_attached, capsys):
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
            with mock.patch.object(
                cfg, "check_lock_info", return_value=(-1, "")
            ):
                main_error_handler(action_disable)(args_mock, cfg)

        _out, err = capsys.readouterr()

        assert (
            messages.E_INVALID_OPTION_COMBINATION.format(
                option1="--purge", option2="--assume-yes"
            ).msg
            in err.strip()
        )
