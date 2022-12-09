import contextlib
import io
import json
import textwrap

import mock
import pytest

from uaclient import defaults, entitlements, event_logger, exceptions, messages
from uaclient.cli import action_enable, main, main_error_handler
from uaclient.entitlements.entitlement_status import (
    CanEnableFailure,
    CanEnableFailureReason,
)

HELP_OUTPUT = """\
usage: pro enable <service> [<service>] [flags]

Enable an Ubuntu Pro service.

Arguments:
  service              the name(s) of the Ubuntu Pro services to enable. One
                       of: cc-eal, cis, esm-apps, esm-infra, fips, fips-
                       updates, livepatch, realtime-kernel, ros, ros-updates

Flags:
  -h, --help           show this help message and exit
  --assume-yes         do not prompt for confirmation before performing the
                       enable
  --access-only        do not auto-install packages. Valid for cc-eal, cis and
                       realtime-kernel.
  --beta               allow beta service to be enabled
  --format {cli,json}  output enable in the specified format (default: cli)
"""


@mock.patch("uaclient.cli.os.getuid")
@mock.patch("uaclient.contract.request_updated_contract")
class TestActionEnable:
    @mock.patch("uaclient.cli.contract.get_available_resources")
    def test_enable_help(
        self,
        _m_resources,
        _getuid,
        _request_updated_contract,
        capsys,
        FakeConfig,
    ):
        with pytest.raises(SystemExit):
            with mock.patch("sys.argv", ["/usr/bin/ua", "enable", "--help"]):
                with mock.patch(
                    "uaclient.config.UAConfig",
                    return_value=FakeConfig(),
                ):
                    main()
        out, _err = capsys.readouterr()
        assert HELP_OUTPUT == out

    @mock.patch("uaclient.cli.contract.get_available_resources")
    def test_non_root_users_are_rejected(
        self,
        _m_resources,
        _request_updated_contract,
        getuid,
        capsys,
        event,
        FakeConfig,
    ):
        """Check that a UID != 0 will receive a message and exit non-zero"""
        getuid.return_value = 1
        args = mock.MagicMock()

        cfg = FakeConfig.for_attached_machine()
        with pytest.raises(exceptions.NonRootUserError):
            action_enable(args, cfg=cfg)

        with pytest.raises(SystemExit):
            with mock.patch(
                "sys.argv",
                [
                    "/usr/bin/ua",
                    "enable",
                    "foobar",
                    "--assume-yes",
                    "--format",
                    "json",
                ],
            ):
                with mock.patch(
                    "uaclient.config.UAConfig",
                    return_value=FakeConfig(),
                ):
                    main()

        expected_message = messages.NONROOT_USER
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
        assert expected == json.loads(capsys.readouterr()[0])

    @mock.patch("uaclient.system.subp")
    def test_lock_file_exists(
        self,
        m_subp,
        _request_updated_contract,
        getuid,
        capsys,
        event,
        FakeConfig,
    ):
        """Check inability to enable if operation holds lock file."""
        getuid.return_value = 0
        cfg = FakeConfig.for_attached_machine()
        cfg.write_cache("lock", "123:pro disable")
        args = mock.MagicMock()

        with pytest.raises(exceptions.LockHeldError) as err:
            action_enable(args, cfg=cfg)
        assert [mock.call(["ps", "123"])] == m_subp.call_args_list

        expected_message = messages.LOCK_HELD_ERROR.format(
            lock_request="pro enable", lock_holder="pro disable", pid="123"
        )
        assert expected_message.msg == err.value.msg

        with pytest.raises(SystemExit):
            with mock.patch.object(
                event, "_event_logger_mode", event_logger.EventLoggerMode.JSON
            ):
                with mock.patch.object(
                    cfg, "check_lock_info"
                ) as m_check_lock_info:
                    m_check_lock_info.return_value = (1, "lock_holder")
                    main_error_handler(action_enable)(args, cfg)

        expected_msg = messages.LOCK_HELD_ERROR.format(
            lock_request="pro enable", lock_holder="lock_holder", pid=1
        )
        expected = {
            "_schema_version": event_logger.JSON_SCHEMA_VERSION,
            "result": "failure",
            "errors": [
                {
                    "message": expected_msg.msg,
                    "message_code": expected_msg.name,
                    "service": None,
                    "type": "system",
                }
            ],
            "failed_services": [],
            "needs_reboot": False,
            "processed_services": [],
            "warnings": [],
        }
        assert expected == json.loads(capsys.readouterr()[0])

    @pytest.mark.parametrize(
        "uid,expected_error_template",
        [
            (0, messages.VALID_SERVICE_FAILURE_UNATTACHED),
            (1000, messages.NONROOT_USER),
        ],
    )
    def test_unattached_error_message(
        self,
        _request_updated_contract,
        m_getuid,
        uid,
        expected_error_template,
        capsys,
        event,
        FakeConfig,
    ):
        """Check that root user gets unattached message."""

        m_getuid.return_value = uid

        cfg = FakeConfig()
        args = mock.MagicMock()
        args.command = "enable"
        args.service = ["esm-infra"]

        if not uid:
            expected_error = expected_error_template.format(
                valid_service="esm-infra"
            )
        else:
            expected_error = expected_error_template

        with pytest.raises(exceptions.UserFacingError) as err:
            action_enable(args, cfg)
        assert expected_error.msg == err.value.msg

        with pytest.raises(SystemExit):
            with mock.patch.object(
                event, "_event_logger_mode", event_logger.EventLoggerMode.JSON
            ):
                main_error_handler(action_enable)(args, cfg)

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
        assert expected == json.loads(capsys.readouterr()[0])

    @pytest.mark.parametrize("is_attached", (True, False))
    @pytest.mark.parametrize(
        "uid,expected_error_template",
        [
            (0, messages.INVALID_SERVICE_OP_FAILURE),
            (1000, messages.NONROOT_USER),
        ],
    )
    def test_invalid_service_error_message(
        self,
        _request_updated_contract,
        m_getuid,
        uid,
        expected_error_template,
        is_attached,
        event,
        FakeConfig,
    ):
        """Check invalid service name results in custom error message."""

        m_getuid.return_value = uid
        if is_attached:
            cfg = FakeConfig.for_attached_machine()
            service_msg = "\n".join(
                textwrap.wrap(
                    (
                        "Try "
                        + ", ".join(
                            entitlements.valid_services(
                                cfg=cfg, allow_beta=True
                            )
                        )
                        + "."
                    ),
                    width=80,
                    break_long_words=False,
                    break_on_hyphens=False,
                )
            )
        else:
            cfg = FakeConfig()
            service_msg = "See {}".format(defaults.BASE_UA_URL)

        args = mock.MagicMock()
        args.service = ["bogus"]
        args.command = "enable"
        with pytest.raises(exceptions.UserFacingError) as err:
            action_enable(args, cfg)

        if not uid:
            expected_error = expected_error_template.format(
                operation="enable",
                invalid_service="bogus",
                service_msg=service_msg,
            )
        else:
            expected_error = expected_error_template

        assert expected_error.msg == err.value.msg

        with pytest.raises(SystemExit):
            with mock.patch.object(
                event, "_event_logger_mode", event_logger.EventLoggerMode.JSON
            ):
                fake_stdout = io.StringIO()
                with contextlib.redirect_stdout(fake_stdout):
                    main_error_handler(action_enable)(args, cfg)

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
            "failed_services": ["bogus"] if not uid and is_attached else [],
            "needs_reboot": False,
            "processed_services": [],
            "warnings": [],
        }
        assert expected == json.loads(fake_stdout.getvalue())

    @pytest.mark.parametrize(
        "uid,expected_error_template",
        [
            (0, messages.MIXED_SERVICES_FAILURE_UNATTACHED),
            (1000, messages.NONROOT_USER),
        ],
    )
    def test_unattached_invalid_and_valid_service_error_message(
        self,
        _request_updated_contract,
        m_getuid,
        uid,
        expected_error_template,
        event,
        FakeConfig,
    ):
        """Check invalid service name results in custom error message."""

        m_getuid.return_value = uid
        cfg = FakeConfig()

        args = mock.MagicMock()
        args.service = ["bogus", "fips"]
        args.command = "enable"
        with pytest.raises(exceptions.UserFacingError) as err:
            action_enable(args, cfg)

        if not uid:
            expected_error = expected_error_template.format(
                operation="enable",
                valid_service="fips",
                invalid_service="bogus",
                service_msg="",
            )
        else:
            expected_error = expected_error_template

        assert expected_error.msg == err.value.msg

        with pytest.raises(SystemExit):
            with mock.patch.object(
                event, "_event_logger_mode", event_logger.EventLoggerMode.JSON
            ):
                fake_stdout = io.StringIO()
                with contextlib.redirect_stdout(fake_stdout):
                    main_error_handler(action_enable)(args, cfg)

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
        assert expected == json.loads(fake_stdout.getvalue())

    @pytest.mark.parametrize("assume_yes", (True, False))
    @mock.patch("uaclient.status.get_available_resources", return_value={})
    @mock.patch("uaclient.entitlements.valid_services")
    def test_assume_yes_passed_to_service_init(
        self,
        m_valid_services,
        _m_get_available_resources,
        m_request_updated_contract,
        m_getuid,
        assume_yes,
        FakeConfig,
    ):
        """assume-yes parameter is passed to entitlement instantiation."""
        m_getuid.return_value = 0

        m_entitlement_cls = mock.MagicMock()
        m_valid_services.return_value = ["testitlement"]
        m_entitlement_obj = m_entitlement_cls.return_value
        m_entitlement_obj.enable.return_value = (True, None)

        cfg = FakeConfig.for_attached_machine()
        args = mock.MagicMock()
        args.service = ["testitlement"]
        args.assume_yes = assume_yes
        args.beta = False
        args.access_only = False

        with mock.patch(
            "uaclient.entitlements.entitlement_factory",
            return_value=m_entitlement_cls,
        ):
            action_enable(args, cfg)

        assert [
            mock.call(
                cfg,
                assume_yes=assume_yes,
                allow_beta=False,
                called_name="testitlement",
                access_only=False,
            )
        ] == m_entitlement_cls.call_args_list

    @mock.patch("uaclient.status.get_available_resources", return_value={})
    @mock.patch("uaclient.entitlements.entitlement_factory")
    @mock.patch("uaclient.entitlements.valid_services")
    def test_entitlements_not_found_disabled_and_enabled(
        self,
        m_valid_services,
        m_entitlement_factory,
        _m_get_available_resources,
        _m_request_updated_contract,
        m_getuid,
        event,
        FakeConfig,
    ):
        m_getuid.return_value = 0
        expected_error_tmpl = messages.INVALID_SERVICE_OP_FAILURE

        m_ent1_cls = mock.Mock()
        m_ent1_obj = m_ent1_cls.return_value
        m_ent1_obj.enable.return_value = (False, None)

        m_ent2_cls = mock.Mock()
        m_ent2_cls.name = "ent2"
        m_ent2_is_beta = mock.PropertyMock(return_value=True)
        type(m_ent2_cls).is_beta = m_ent2_is_beta
        m_ent2_obj = m_ent2_cls.return_value
        m_ent2_obj.enable.return_value = (
            False,
            CanEnableFailure(CanEnableFailureReason.IS_BETA),
        )

        m_ent3_cls = mock.Mock()
        m_ent3_cls.name = "ent3"
        m_ent3_is_beta = mock.PropertyMock(return_value=False)
        type(m_ent3_cls).is_beta = m_ent3_is_beta
        m_ent3_obj = m_ent3_cls.return_value
        m_ent3_obj.enable.return_value = (True, None)

        def factory_side_effect(cfg, name, not_found_okay=True):
            if name == "ent2":
                return m_ent2_cls
            if name == "ent3":
                return m_ent3_cls
            return None

        m_entitlement_factory.side_effect = factory_side_effect
        m_valid_services.return_value = ["ent2", "ent3"]

        cfg = FakeConfig.for_attached_machine()
        assume_yes = False
        args_mock = mock.Mock()
        args_mock.service = ["ent1", "ent2", "ent3"]
        args_mock.access_only = False
        args_mock.assume_yes = assume_yes
        args_mock.beta = False

        expected_msg = "One moment, checking your subscription first\n"

        with pytest.raises(exceptions.UserFacingError) as err:
            fake_stdout = io.StringIO()
            with contextlib.redirect_stdout(fake_stdout):
                action_enable(args_mock, cfg)

        expected_error = expected_error_tmpl.format(
            operation="enable",
            invalid_service="ent1, ent2",
            service_msg=(
                "Try "
                + ", ".join(entitlements.valid_services(allow_beta=False))
                + "."
            ),
        )
        assert expected_error.msg == err.value.msg
        assert expected_msg == fake_stdout.getvalue()

        for m_ent_cls in [m_ent2_cls, m_ent3_cls]:
            assert [
                mock.call(
                    cfg,
                    assume_yes=assume_yes,
                    allow_beta=False,
                    called_name=m_ent_cls.name,
                    access_only=False,
                )
            ] == m_ent_cls.call_args_list

        expected_enable_call = mock.call()
        for m_ent in [m_ent2_obj, m_ent3_obj]:
            assert [expected_enable_call] == m_ent.enable.call_args_list

        assert 0 == m_ent1_obj.call_count

        event.reset()
        with pytest.raises(SystemExit):
            with mock.patch.object(
                event, "_event_logger_mode", event_logger.EventLoggerMode.JSON
            ):
                fake_stdout = io.StringIO()
                with contextlib.redirect_stdout(fake_stdout):
                    main_error_handler(action_enable)(args_mock, cfg)

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
            "failed_services": ["ent1", "ent2"],
            "needs_reboot": False,
            "processed_services": ["ent3"],
            "warnings": [],
        }
        assert expected == json.loads(fake_stdout.getvalue())

    @pytest.mark.parametrize("beta_flag", ((False), (True)))
    @mock.patch("uaclient.status.get_available_resources", return_value={})
    @mock.patch("uaclient.entitlements.entitlement_factory")
    @mock.patch("uaclient.entitlements.valid_services")
    def test_entitlements_not_found_and_beta(
        self,
        m_valid_services,
        m_entitlement_factory,
        _m_get_available_resources,
        _m_request_updated_contract,
        m_getuid,
        beta_flag,
        event,
        FakeConfig,
    ):
        m_getuid.return_value = 0
        expected_error_tmpl = messages.INVALID_SERVICE_OP_FAILURE

        m_ent1_cls = mock.Mock()
        m_ent1_obj = m_ent1_cls.return_value
        m_ent1_obj.enable.return_value = (False, None)

        m_ent2_cls = mock.Mock()
        m_ent2_cls.name = "ent2"
        m_ent2_is_beta = mock.PropertyMock(return_value=True)
        type(m_ent2_cls)._is_beta = m_ent2_is_beta
        m_ent2_obj = m_ent2_cls.return_value
        failure_reason = CanEnableFailure(CanEnableFailureReason.IS_BETA)
        if beta_flag:
            m_ent2_obj.enable.return_value = (True, None)
        else:
            m_ent2_obj.enable.return_value = (False, failure_reason)

        m_ent3_cls = mock.Mock()
        m_ent3_cls.name = "ent3"
        m_ent3_is_beta = mock.PropertyMock(return_value=False)
        type(m_ent3_cls)._is_beta = m_ent3_is_beta
        m_ent3_obj = m_ent3_cls.return_value
        m_ent3_obj.enable.return_value = (True, None)

        cfg = FakeConfig.for_attached_machine()
        assume_yes = False
        args_mock = mock.Mock()
        args_mock.service = ["ent1", "ent2", "ent3"]
        args_mock.access_only = False
        args_mock.assume_yes = assume_yes
        args_mock.beta = beta_flag

        def factory_side_effect(cfg, name, not_found_okay=True):
            if name == "ent2":
                return m_ent2_cls
            if name == "ent3":
                return m_ent3_cls
            return None

        m_entitlement_factory.side_effect = factory_side_effect

        def valid_services_side_effect(cfg, allow_beta, all_names=False):
            if allow_beta:
                return ["ent2", "ent3"]
            return ["ent2"]

        m_valid_services.side_effect = valid_services_side_effect

        expected_msg = "One moment, checking your subscription first\n"
        not_found_name = "ent1"
        mock_ent_list = [m_ent3_cls]
        mock_obj_list = [m_ent3_obj]

        service_names = entitlements.valid_services(cfg, allow_beta=beta_flag)
        ent_str = "Try " + ", ".join(service_names) + "."
        if not beta_flag:
            not_found_name += ", ent2"
        else:
            mock_ent_list.append(m_ent2_cls)
            mock_obj_list.append(m_ent3_obj)
        service_msg = "\n".join(
            textwrap.wrap(
                ent_str,
                width=80,
                break_long_words=False,
                break_on_hyphens=False,
            )
        )

        with pytest.raises(exceptions.UserFacingError) as err:
            fake_stdout = io.StringIO()
            with contextlib.redirect_stdout(fake_stdout):
                action_enable(args_mock, cfg)

        expected_error = expected_error_tmpl.format(
            operation="enable",
            invalid_service=not_found_name,
            service_msg=service_msg,
        )
        assert expected_error.msg == err.value.msg
        assert expected_msg == fake_stdout.getvalue()

        for m_ent_cls in mock_ent_list:
            assert [
                mock.call(
                    cfg,
                    assume_yes=assume_yes,
                    allow_beta=beta_flag,
                    called_name=m_ent_cls.name,
                    access_only=False,
                )
            ] == m_ent_cls.call_args_list

        expected_enable_call = mock.call()
        for m_ent in mock_obj_list:
            assert [expected_enable_call] == m_ent.enable.call_args_list

        assert 0 == m_ent1_obj.call_count

        event.reset()
        with pytest.raises(SystemExit):
            with mock.patch.object(
                event, "_event_logger_mode", event_logger.EventLoggerMode.JSON
            ):
                fake_stdout = io.StringIO()
                with contextlib.redirect_stdout(fake_stdout):
                    main_error_handler(action_enable)(args_mock, cfg=cfg)

        expected_failed_services = ["ent1", "ent2"]
        if beta_flag:
            expected_failed_services = ["ent1"]

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
            "failed_services": expected_failed_services,
            "needs_reboot": False,
            "processed_services": ["ent2", "ent3"] if beta_flag else ["ent3"],
            "warnings": [],
        }
        assert expected == json.loads(fake_stdout.getvalue())

    @mock.patch("uaclient.status.get_available_resources", return_value={})
    def test_print_message_when_can_enable_fails(
        self,
        _m_get_available_resources,
        _m_request_updated_contract,
        m_getuid,
        event,
        FakeConfig,
    ):
        m_getuid.return_value = 0
        m_entitlement_cls = mock.Mock()
        type(m_entitlement_cls).is_beta = mock.PropertyMock(return_value=False)
        m_entitlement_obj = m_entitlement_cls.return_value
        m_entitlement_obj.enable.return_value = (
            False,
            CanEnableFailure(
                CanEnableFailureReason.ALREADY_ENABLED,
                message=messages.NamedMessage("test-code", "msg"),
            ),
        )

        cfg = FakeConfig.for_attached_machine()
        args_mock = mock.Mock()
        args_mock.service = ["ent1"]
        args_mock.assume_yes = False
        args_mock.beta = False

        with mock.patch(
            "uaclient.entitlements.entitlement_factory",
            return_value=m_entitlement_cls,
        ), mock.patch(
            "uaclient.entitlements.valid_services", return_value=["ent1"]
        ):
            fake_stdout = io.StringIO()
            with contextlib.redirect_stdout(fake_stdout):
                action_enable(args_mock, cfg)

            assert (
                "One moment, checking your subscription first\nmsg\n"
                == fake_stdout.getvalue()
            )

        with mock.patch(
            "uaclient.entitlements.entitlement_factory",
            return_value=m_entitlement_cls,
        ), mock.patch(
            "uaclient.entitlements.valid_services", return_value=["ent1"]
        ), mock.patch.object(
            event, "_event_logger_mode", event_logger.EventLoggerMode.JSON
        ):
            fake_stdout = io.StringIO()
            with contextlib.redirect_stdout(fake_stdout):
                ret = action_enable(args_mock, cfg=cfg)

        expected_ret = 1
        expected = {
            "_schema_version": event_logger.JSON_SCHEMA_VERSION,
            "result": "failure",
            "errors": [
                {
                    "message": "msg",
                    "message_code": "test-code",
                    "service": "ent1",
                    "type": "service",
                }
            ],
            "failed_services": ["ent1"],
            "needs_reboot": False,
            "processed_services": [],
            "warnings": [],
        }
        assert expected == json.loads(fake_stdout.getvalue())
        assert expected_ret == ret

    @pytest.mark.parametrize(
        "service, beta",
        ((["bogus"], False), (["bogus"], True), (["bogus1", "bogus2"], False)),
    )
    def test_invalid_service_names(
        self,
        _m_request_updated_contract,
        m_getuid,
        service,
        beta,
        event,
        FakeConfig,
    ):
        m_getuid.return_value = 0
        expected_error_tmpl = messages.INVALID_SERVICE_OP_FAILURE
        expected_msg = "One moment, checking your subscription first\n"

        cfg = FakeConfig.for_attached_machine()
        args_mock = mock.MagicMock()
        args_mock.service = service
        args_mock.beta = beta

        with pytest.raises(exceptions.UserFacingError) as err:
            fake_stdout = io.StringIO()
            with contextlib.redirect_stdout(fake_stdout):
                action_enable(args_mock, cfg)

        assert expected_msg == fake_stdout.getvalue()

        service_names = entitlements.valid_services(cfg=cfg, allow_beta=beta)
        ent_str = "Try " + ", ".join(service_names) + "."
        service_msg = "\n".join(
            textwrap.wrap(
                ent_str,
                width=80,
                break_long_words=False,
                break_on_hyphens=False,
            )
        )
        expected_error = expected_error_tmpl.format(
            operation="enable",
            invalid_service=", ".join(sorted(service)),
            service_msg=service_msg,
        )
        assert expected_error.msg == err.value.msg

        with pytest.raises(SystemExit):
            with mock.patch.object(
                event, "_event_logger_mode", event_logger.EventLoggerMode.JSON
            ):
                fake_stdout = io.StringIO()
                with contextlib.redirect_stdout(fake_stdout):
                    main_error_handler(action_enable)(args_mock, cfg)

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
            "failed_services": service,
            "needs_reboot": False,
            "processed_services": [],
            "warnings": [],
        }
        assert expected == json.loads(fake_stdout.getvalue())

    @pytest.mark.parametrize("allow_beta", ((True), (False)))
    @mock.patch("uaclient.status.get_available_resources", return_value={})
    @mock.patch("uaclient.status.status")
    def test_entitlement_instantiated_and_enabled(
        self,
        m_status,
        _m_get_available_resources,
        _m_request_updated_contract,
        m_getuid,
        allow_beta,
        event,
        FakeConfig,
    ):
        m_getuid.return_value = 0
        m_entitlement_cls = mock.Mock()
        m_entitlement_obj = m_entitlement_cls.return_value
        m_entitlement_obj.enable.return_value = (True, None)

        cfg = FakeConfig.for_attached_machine()

        args_mock = mock.MagicMock()
        args_mock.access_only = False
        args_mock.assume_yes = False
        args_mock.beta = allow_beta
        args_mock.service = ["testitlement"]

        with mock.patch(
            "uaclient.entitlements.entitlement_factory",
            return_value=m_entitlement_cls,
        ), mock.patch(
            "uaclient.entitlements.valid_services",
            return_value=["testitlement"],
        ):
            ret = action_enable(args_mock, cfg)

        assert [
            mock.call(
                cfg,
                assume_yes=False,
                allow_beta=allow_beta,
                called_name="testitlement",
                access_only=False,
            )
        ] == m_entitlement_cls.call_args_list

        m_entitlement = m_entitlement_cls.return_value
        expected_enable_call = mock.call()
        expected_ret = 0
        assert [expected_enable_call] == m_entitlement.enable.call_args_list
        assert expected_ret == ret
        assert 1 == m_status.call_count

        with mock.patch(
            "uaclient.entitlements.entitlement_factory",
            return_value=m_entitlement_cls,
        ), mock.patch(
            "uaclient.entitlements.valid_services",
            return_value=["testitlement"],
        ), mock.patch.object(
            event, "_event_logger_mode", event_logger.EventLoggerMode.JSON
        ):
            fake_stdout = io.StringIO()
            with contextlib.redirect_stdout(fake_stdout):
                ret = action_enable(args_mock, cfg=cfg)

        expected = {
            "_schema_version": event_logger.JSON_SCHEMA_VERSION,
            "result": "success",
            "errors": [],
            "failed_services": [],
            "needs_reboot": False,
            "processed_services": ["testitlement"],
            "warnings": [],
        }
        assert expected == json.loads(fake_stdout.getvalue())
        assert expected_ret == ret

    def test_format_json_fails_when_assume_yes_flag_not_used(
        self, _m_get_available_resources, _m_getuid, event
    ):
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
                    main_error_handler(action_enable)(args_mock, cfg)

        expected_message = messages.JSON_FORMAT_REQUIRE_ASSUME_YES
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
