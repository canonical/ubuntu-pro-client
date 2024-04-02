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
from uaclient.cli import main, main_error_handler
from uaclient.cli.enable import action_enable, prompt_for_dependency_handling
from uaclient.entitlements.entitlement_status import (
    CanEnableFailure,
    CanEnableFailureReason,
)
from uaclient.files.user_config_file import UserConfigData
from uaclient.testing.helpers import does_not_raise

HELP_OUTPUT = """\
usage: pro enable <service> [<service>] [flags]

Enable an Ubuntu Pro service.

Arguments:
  service              the name(s) of the Ubuntu Pro services to enable. One
                       of: anbox-cloud, cc-eal, cis, esm-apps, esm-infra,
                       fips, fips-preview, fips-updates, landscape, livepatch,
                       realtime-kernel, ros, ros-updates

Flags:
  -h, --help           show this help message and exit
  --assume-yes         do not prompt for confirmation before performing the
                       enable
  --access-only        do not auto-install packages. Valid for cc-eal, cis and
                       realtime-kernel.
  --beta               allow beta service to be enabled
  --format {cli,json}  output in the specified format (default: cli)
  --variant VARIANT    The name of the variant to use when enabling the
                       service
"""


@mock.patch(
    "uaclient.files.user_config_file.UserConfigFileObject.public_config",
    new_callable=mock.PropertyMock,
    return_value=UserConfigData(),
)
@mock.patch("uaclient.contract.UAContractClient.update_activity_token")
@mock.patch("uaclient.contract.refresh")
class TestActionEnable:
    @mock.patch("uaclient.log.setup_cli_logging")
    @mock.patch("uaclient.cli.contract.get_available_resources")
    def test_enable_help(
        self,
        _m_resources,
        _m_setup_logging,
        _refresh,
        _m_update_activity_token,
        _m_public_config,
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

    @mock.patch("uaclient.log.setup_cli_logging")
    @mock.patch("uaclient.util.we_are_currently_root", return_value=False)
    @mock.patch("uaclient.cli.contract.get_available_resources")
    def test_non_root_users_are_rejected(
        self,
        _m_resources,
        _refresh,
        we_are_currently_root,
        m_setup_logging,
        _m_update_activity_token,
        _m_public_config,
        capsys,
        event,
        FakeConfig,
        tmpdir,
    ):
        """Check that a UID != 0 will receive a message and exit non-zero"""
        args = mock.MagicMock()

        cfg = FakeConfig.for_attached_machine()
        with pytest.raises(exceptions.NonRootUserError):
            action_enable(args, cfg=cfg)

        default_get_user_log_file = tmpdir.join("default.log").strpath
        defaults_ret = {
            "log_level": "debug",
            "log_file": default_get_user_log_file,
        }

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
                    with mock.patch(
                        "uaclient.log.get_user_log_file",
                        return_value=tmpdir.join("user.log").strpath,
                    ):
                        with mock.patch.dict(
                            "uaclient.cli.defaults.CONFIG_DEFAULTS",
                            defaults_ret,
                        ):
                            main()

        expected_message = messages.E_NONROOT_USER
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

    @mock.patch("uaclient.lock.check_lock_info")
    @mock.patch("time.sleep")
    @mock.patch("uaclient.system.subp")
    def test_lock_file_exists(
        self,
        m_subp,
        m_sleep,
        m_check_lock_info,
        _refresh,
        _m_update_activity_token,
        _m_public_config,
        capsys,
        event,
        FakeConfig,
    ):
        """Check inability to enable if operation holds lock file."""
        cfg = FakeConfig.for_attached_machine()
        m_check_lock_info.return_value = (123, "pro disable")
        args = mock.MagicMock()

        with pytest.raises(exceptions.LockHeldError) as err:
            action_enable(args, cfg=cfg)
        assert 12 == m_check_lock_info.call_count

        expected_msg = messages.E_LOCK_HELD_ERROR.format(
            lock_request="pro enable", lock_holder="pro disable", pid="123"
        )
        assert expected_msg.msg == err.value.msg

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
                    "additional_info": {
                        "lock_holder": "pro disable",
                        "lock_request": "pro enable",
                        "pid": 123,
                    },
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
        _refresh,
        _m_update_activity_token,
        _m_public_config,
        root,
        expected_error_template,
        capsys,
        event,
        FakeConfig,
    ):
        """Check that root user gets unattached message."""

        m_we_are_currently_root.return_value = root

        cfg = FakeConfig()
        args = mock.MagicMock()
        args.command = "enable"
        args.service = ["esm-infra"]

        if root:
            expected_error = expected_error_template.format(
                valid_service="esm-infra", operation="enable"
            )
            expected_info = {
                "valid_service": "esm-infra",
                "operation": "enable",
            }
        else:
            expected_error = expected_error_template
            expected_info = None

        with pytest.raises(exceptions.UbuntuProError) as err:
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
        if expected_info is not None:
            expected["errors"][0]["additional_info"] = expected_info
        assert expected == json.loads(capsys.readouterr()[0])

    @pytest.mark.parametrize("is_attached", (True, False))
    @pytest.mark.parametrize(
        "root,expected_error_template",
        [
            (True, messages.E_INVALID_SERVICE_OP_FAILURE),
            (False, messages.E_NONROOT_USER),
        ],
    )
    @mock.patch("uaclient.lock.check_lock_info", return_value=(-1, ""))
    @mock.patch("uaclient.util.we_are_currently_root")
    def test_invalid_service_error_message(
        self,
        m_we_are_currently_root,
        _m_check_lock_info,
        _refresh,
        _m_update_activity_token,
        _m_public_config,
        root,
        expected_error_template,
        is_attached,
        event,
        FakeConfig,
    ):
        """Check invalid service name results in custom error message."""

        m_we_are_currently_root.return_value = root
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
            service_msg = ""

        args = mock.MagicMock()
        args.service = ["bogus"]
        args.command = "enable"
        args.access_only = False

        fake_stdout = io.StringIO()
        if root and is_attached:
            expected_err = does_not_raise()
        else:
            expected_err = pytest.raises(exceptions.UbuntuProError)
        with expected_err as err:
            with mock.patch.object(lock, "lock_data_file"):
                with contextlib.redirect_stdout(fake_stdout):
                    action_enable(args, cfg=cfg)

        if root:
            expected_error = expected_error_template.format(
                operation="enable",
                invalid_service="bogus",
                service_msg=service_msg,
            )
            expected_info = {
                "invalid_service": "bogus",
                "operation": "enable",
                "service_msg": service_msg,
            }
        else:
            expected_error = expected_error_template
            expected_info = None

        if root and is_attached:
            assert expected_error.msg in fake_stdout.getvalue()
        else:
            assert expected_error.msg == err.value.msg

        args.assume_yes = True
        args.format = "json"
        if root and is_attached:
            expected_err = does_not_raise()
        else:
            expected_err = pytest.raises(SystemExit)
        with expected_err:
            with mock.patch.object(
                event, "_event_logger_mode", event_logger.EventLoggerMode.JSON
            ):
                with mock.patch.object(lock, "lock_data_file"):
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
            "failed_services": ["bogus"] if root and is_attached else [],
            "needs_reboot": False,
            "processed_services": [],
            "warnings": [],
        }
        if expected_info is not None:
            expected["errors"][0]["additional_info"] = expected_info
        assert expected == json.loads(fake_stdout.getvalue())

    @pytest.mark.parametrize(
        "root,expected_error_template",
        [
            (True, messages.E_MIXED_SERVICES_FAILURE_UNATTACHED),
            (False, messages.E_NONROOT_USER),
        ],
    )
    @mock.patch("uaclient.util.we_are_currently_root")
    def test_unattached_invalid_and_valid_service_error_message(
        self,
        m_we_are_currently_root,
        _refresh,
        _m_update_activity_token,
        _m_public_config,
        root,
        expected_error_template,
        event,
        FakeConfig,
    ):
        """Check invalid service name results in custom error message."""

        m_we_are_currently_root.return_value = root
        cfg = FakeConfig()

        args = mock.MagicMock()
        args.service = ["bogus", "fips"]
        args.command = "enable"
        with pytest.raises(exceptions.UbuntuProError) as err:
            action_enable(args, cfg)

        if root:
            expected_error = expected_error_template.format(
                operation="enable",
                valid_service="fips",
                invalid_service="bogus",
                service_msg="",
            )
            expected_info = {
                "invalid_service": "bogus",
                "operation": "enable",
                "service_msg": "",
                "valid_service": "fips",
            }
        else:
            expected_error = expected_error_template
            expected_info = None

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
        if expected_info is not None:
            expected["errors"][0]["additional_info"] = expected_info
        assert expected == json.loads(fake_stdout.getvalue())

    @pytest.mark.parametrize("assume_yes", (True, False))
    @mock.patch("uaclient.files.state_files.status_cache_file.write")
    @mock.patch("uaclient.lock.check_lock_info", return_value=(-1, ""))
    @mock.patch("uaclient.status.get_available_resources", return_value={})
    @mock.patch("uaclient.entitlements.valid_services")
    def test_assume_yes_passed_to_service_init(
        self,
        m_valid_services,
        _m_get_available_resources,
        _m_check_lock_info,
        _m_status_cache_file,
        m_refresh,
        _m_update_activity_token,
        _m_public_config,
        assume_yes,
        FakeConfig,
    ):
        """assume-yes parameter is passed to entitlement instantiation."""

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
        args.variant = ""

        with mock.patch(
            "uaclient.entitlements.entitlement_factory",
            return_value=m_entitlement_cls,
        ):
            with mock.patch.object(lock, "lock_data_file"):
                action_enable(args, cfg)

        assert [
            mock.call(
                cfg,
                assume_yes=assume_yes,
                allow_beta=False,
                called_name="testitlement",
                access_only=False,
                extra_args=None,
            ),
        ] == m_entitlement_cls.call_args_list

    @mock.patch("uaclient.files.state_files.status_cache_file.write")
    @mock.patch("uaclient.lock.check_lock_info", return_value=(-1, ""))
    @mock.patch("uaclient.status.get_available_resources", return_value={})
    @mock.patch("uaclient.entitlements.entitlement_factory")
    @mock.patch("uaclient.entitlements.valid_services")
    def test_entitlements_not_found_disabled_and_enabled(
        self,
        m_valid_services,
        m_entitlement_factory,
        _m_get_available_resources,
        _m_check_lock_info,
        _m_refresh,
        _m_status_cache_file,
        _m_update_activity_token,
        _m_public_config,
        event,
        FakeConfig,
    ):
        expected_error_tmpl = messages.E_INVALID_SERVICE_OP_FAILURE

        m_ent1_cls = mock.MagicMock()
        m_ent1_obj = m_ent1_cls.return_value
        type(m_ent1_obj).title = mock.PropertyMock(return_value="Ent1")
        m_ent1_obj.enable.return_value = (False, None)
        m_ent1_obj._check_for_reboot.return_value = False

        m_ent2_cls = mock.MagicMock()
        m_ent2_cls.name = "ent2"
        m_ent2_is_beta = mock.PropertyMock(return_value=True)
        type(m_ent2_cls).is_beta = m_ent2_is_beta
        m_ent2_obj = m_ent2_cls.return_value
        type(m_ent2_obj).title = mock.PropertyMock(return_value="Ent2")
        m_ent2_obj._check_for_reboot.return_value = False
        m_ent2_obj.enable.return_value = (
            False,
            CanEnableFailure(CanEnableFailureReason.IS_BETA),
        )

        m_ent3_cls = mock.MagicMock()
        m_ent3_cls.name = "ent3"
        m_ent3_is_beta = mock.PropertyMock(return_value=False)
        type(m_ent3_cls).is_beta = m_ent3_is_beta
        m_ent3_obj = m_ent3_cls.return_value
        type(m_ent3_obj).title = mock.PropertyMock(return_value="Ent3")
        m_ent3_obj.enable.return_value = (True, None)
        m_ent3_obj._check_for_reboot.return_value = False

        def factory_side_effect(cfg, name, variant=""):
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
        args_mock.variant = ""

        expected_msg = (
            "One moment, checking your subscription first\n"
            "Could not enable Ent2.\n"
            "Ent3 enabled\n"
        )

        with mock.patch.object(lock, "lock_data_file"):
            fake_stdout = io.StringIO()
            with contextlib.redirect_stdout(fake_stdout):
                action_enable(args_mock, cfg=cfg)

        service_msg = (
            "Try "
            + ", ".join(entitlements.valid_services(allow_beta=False))
            + "."
        )
        expected_error = expected_error_tmpl.format(
            operation="enable",
            invalid_service="ent1, ent2",
            service_msg=service_msg,
        )
        assert (
            expected_msg + expected_error.msg + "\n" == fake_stdout.getvalue()
        )

        for m_ent_cls in [m_ent2_cls, m_ent3_cls]:
            assert [
                mock.call(
                    cfg,
                    assume_yes=assume_yes,
                    allow_beta=False,
                    called_name=m_ent_cls.name,
                    access_only=False,
                    extra_args=None,
                ),
            ] == m_ent_cls.call_args_list

        expected_enable_call = mock.call(mock.ANY)
        for m_ent in [m_ent2_obj, m_ent3_obj]:
            assert [expected_enable_call] == m_ent.enable.call_args_list

        assert 0 == m_ent1_obj.call_count

        event.reset()
        args_mock.assume_yes = True
        args_mock.format = "json"
        with mock.patch.object(lock, "lock_data_file"):
            fake_stdout = io.StringIO()
            with contextlib.redirect_stdout(fake_stdout):
                main_error_handler(action_enable)(args_mock, cfg)

        expected = {
            "_schema_version": event_logger.JSON_SCHEMA_VERSION,
            "result": "failure",
            "errors": [
                {
                    "additional_info": {
                        "invalid_service": "ent1, ent2",
                        "operation": "enable",
                        "service_msg": service_msg,
                    },
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
    @mock.patch("uaclient.files.state_files.status_cache_file.write")
    @mock.patch("uaclient.lock.check_lock_info", return_value=(-1, ""))
    @mock.patch("uaclient.status.get_available_resources", return_value={})
    @mock.patch("uaclient.entitlements.entitlement_factory")
    @mock.patch("uaclient.entitlements.valid_services")
    def test_entitlements_not_found_and_beta(
        self,
        m_valid_services,
        m_entitlement_factory,
        _m_get_available_resources,
        _m_check_lock_info,
        _m_status_cache_file,
        _m_refresh,
        _m_update_activity_token,
        _m_public_config,
        beta_flag,
        event,
        FakeConfig,
    ):
        expected_error_tmpl = messages.E_INVALID_SERVICE_OP_FAILURE

        m_ent1_cls = mock.MagicMock()
        m_ent1_obj = m_ent1_cls.return_value
        type(m_ent1_obj).title = mock.PropertyMock(return_value="Ent1")
        m_ent1_obj.enable.return_value = (False, None)
        m_ent1_obj._check_for_reboot.return_value = False

        m_ent2_cls = mock.MagicMock()
        m_ent2_cls.name = "ent2"
        m_ent2_is_beta = mock.PropertyMock(return_value=True)
        type(m_ent2_cls)._is_beta = m_ent2_is_beta
        m_ent2_obj = m_ent2_cls.return_value
        type(m_ent2_obj).title = mock.PropertyMock(return_value="Ent2")
        m_ent2_obj._check_for_reboot.return_value = False
        failure_reason = CanEnableFailure(CanEnableFailureReason.IS_BETA)
        if beta_flag:
            m_ent2_obj.enable.return_value = (True, None)
        else:
            m_ent2_obj.enable.return_value = (False, failure_reason)

        m_ent3_cls = mock.MagicMock()
        m_ent3_cls.name = "ent3"
        m_ent3_is_beta = mock.PropertyMock(return_value=False)
        type(m_ent3_cls)._is_beta = m_ent3_is_beta
        m_ent3_obj = m_ent3_cls.return_value
        type(m_ent3_obj).title = mock.PropertyMock(return_value="Ent3")
        m_ent3_obj.enable.return_value = (True, None)
        m_ent3_obj._check_for_reboot.return_value = False

        cfg = FakeConfig.for_attached_machine()
        assume_yes = False
        args_mock = mock.Mock()
        args_mock.service = ["ent1", "ent2", "ent3"]
        args_mock.access_only = False
        args_mock.assume_yes = assume_yes
        args_mock.beta = beta_flag
        args_mock.variant = ""

        def factory_side_effect(cfg, name, variant=""):
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

        if beta_flag:
            expected_msg = (
                "One moment, checking your subscription first\n"
                "Ent2 enabled\n"
                "Ent3 enabled\n"
            )
        else:
            expected_msg = (
                "One moment, checking your subscription first\n"
                "Could not enable Ent2.\n"
                "Ent3 enabled\n"
            )
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

        with mock.patch.object(lock, "lock_data_file"):
            fake_stdout = io.StringIO()
            with contextlib.redirect_stdout(fake_stdout):
                action_enable(args_mock, cfg=cfg)

        expected_error = expected_error_tmpl.format(
            operation="enable",
            invalid_service=not_found_name,
            service_msg=service_msg,
        )
        assert (
            expected_msg + expected_error.msg + "\n" == fake_stdout.getvalue()
        )

        for m_ent_cls in mock_ent_list:
            assert [
                mock.call(
                    cfg,
                    assume_yes=assume_yes,
                    allow_beta=beta_flag,
                    called_name=m_ent_cls.name,
                    access_only=False,
                    extra_args=None,
                ),
            ] == m_ent_cls.call_args_list

        expected_enable_call = mock.call(mock.ANY)
        for m_ent in mock_obj_list:
            assert [expected_enable_call] == m_ent.enable.call_args_list

        assert 0 == m_ent1_obj.call_count

        event.reset()
        args_mock.assume_yes = True
        args_mock.format = "json"
        with mock.patch.object(lock, "lock_data_file"):
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
                    "additional_info": {
                        "invalid_service": ", ".join(
                            sorted(expected_failed_services)
                        ),
                        "operation": "enable",
                        "service_msg": service_msg,
                    },
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

    @mock.patch("uaclient.files.state_files.status_cache_file.write")
    @mock.patch("uaclient.lock.check_lock_info", return_value=(-1, ""))
    @mock.patch("uaclient.status.get_available_resources", return_value={})
    def test_print_message_when_can_enable_fails(
        self,
        _m_get_available_resources,
        _m_check_lock_info,
        _m_status_cache_file,
        _m_refresh,
        _m_update_activity_token,
        _m_public_config,
        event,
        FakeConfig,
    ):
        m_entitlement_cls = mock.MagicMock()
        type(m_entitlement_cls).is_beta = mock.PropertyMock(return_value=False)
        m_entitlement_obj = m_entitlement_cls.return_value
        type(m_entitlement_obj).title = mock.PropertyMock(return_value="Title")
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
        args_mock.access_only = False

        with mock.patch(
            "uaclient.entitlements.entitlement_factory",
            return_value=m_entitlement_cls,
        ), mock.patch(
            "uaclient.entitlements.valid_services", return_value=["ent1"]
        ):
            with mock.patch.object(lock, "lock_data_file"):
                fake_stdout = io.StringIO()
                with contextlib.redirect_stdout(fake_stdout):
                    action_enable(args_mock, cfg=cfg)

            assert (
                "One moment, checking your subscription first\nmsg\n"
                "Could not enable Title.\n"
            ) == fake_stdout.getvalue()

        args_mock.assume_yes = True
        args_mock.format = "json"

        with mock.patch(
            "uaclient.entitlements.entitlement_factory",
            return_value=m_entitlement_cls,
        ), mock.patch(
            "uaclient.entitlements.valid_services", return_value=["ent1"]
        ):
            with mock.patch.object(lock, "lock_data_file"):
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
    @mock.patch("uaclient.lock.check_lock_info", return_value=(-1, ""))
    def test_invalid_service_names(
        self,
        _m_check_lock_info,
        _m_refresh,
        _m_update_activity_token,
        _m_public_config,
        service,
        beta,
        event,
        FakeConfig,
    ):
        expected_error_tmpl = messages.E_INVALID_SERVICE_OP_FAILURE
        expected_msg = "One moment, checking your subscription first\n"

        cfg = FakeConfig.for_attached_machine()
        args_mock = mock.MagicMock()
        args_mock.service = service
        args_mock.beta = beta
        args_mock.access_only = False

        with mock.patch.object(lock, "lock_data_file"):
            fake_stdout = io.StringIO()
            with contextlib.redirect_stdout(fake_stdout):
                action_enable(args_mock, cfg=cfg)

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
        assert (
            expected_msg + expected_error.msg + "\n" == fake_stdout.getvalue()
        )

        args_mock.assume_yes = True
        args_mock.format = "json"

        with mock.patch.object(lock, "lock_data_file"):
            fake_stdout = io.StringIO()
            with contextlib.redirect_stdout(fake_stdout):
                main_error_handler(action_enable)(args_mock, cfg)

        expected = {
            "_schema_version": event_logger.JSON_SCHEMA_VERSION,
            "result": "failure",
            "errors": [
                {
                    "additional_info": {
                        "invalid_service": ", ".join(sorted(service)),
                        "operation": "enable",
                        "service_msg": service_msg,
                    },
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
    @mock.patch("uaclient.lock.check_lock_info", return_value=(-1, ""))
    @mock.patch("uaclient.status.get_available_resources", return_value={})
    @mock.patch("uaclient.status.status")
    def test_entitlement_instantiated_and_enabled(
        self,
        m_status,
        _m_get_available_resources,
        _m_check_lock_info,
        _m_refresh,
        m_update_activity_token,
        _m_public_config,
        allow_beta,
        event,
        FakeConfig,
    ):
        m_entitlement_cls = mock.MagicMock()
        m_entitlement_obj = m_entitlement_cls.return_value
        m_entitlement_obj.enable.return_value = (True, None)
        m_entitlement_obj._check_for_reboot.return_value = False

        cfg = FakeConfig.for_attached_machine()

        args_mock = mock.MagicMock()
        args_mock.access_only = False
        args_mock.assume_yes = True
        args_mock.beta = allow_beta
        args_mock.service = ["testitlement"]
        args_mock.variant = ""
        args_mock.format = "json"

        with mock.patch(
            "uaclient.entitlements.entitlement_factory",
            return_value=m_entitlement_cls,
        ), mock.patch(
            "uaclient.entitlements.valid_services",
            return_value=["testitlement"],
        ):
            with mock.patch.object(lock, "lock_data_file"):
                ret = action_enable(args_mock, cfg=cfg)

        assert [
            mock.call(
                cfg,
                assume_yes=True,
                allow_beta=allow_beta,
                called_name="testitlement",
                access_only=False,
                extra_args=None,
            ),
        ] == m_entitlement_cls.call_args_list

        m_entitlement = m_entitlement_cls.return_value
        expected_enable_call = mock.call(mock.ANY)
        expected_ret = 0
        assert [expected_enable_call] == m_entitlement.enable.call_args_list
        assert expected_ret == ret
        assert 1 == m_status.call_count
        assert 1 == m_update_activity_token.call_count

        with mock.patch(
            "uaclient.entitlements.entitlement_factory",
            return_value=m_entitlement_cls,
        ), mock.patch(
            "uaclient.entitlements.valid_services",
            return_value=["testitlement"],
        ):
            with mock.patch.object(lock, "lock_data_file"):
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
        self,
        _m_get_available_resources,
        _m_update_activity_token,
        _m_public_config,
        event,
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
    def test_access_only_cannot_be_used_together_with_variant(
        self,
        _m_check_lock_info,
        _m_get_available_resources,
        _m_update_activity_token,
        _m_public_config,
        FakeConfig,
    ):
        cfg = FakeConfig.for_attached_machine()
        args_mock = mock.MagicMock()
        args_mock.access_only = True
        args_mock.variant = "variant"

        with pytest.raises(exceptions.InvalidOptionCombination):
            with mock.patch.object(lock, "lock_data_file"):
                action_enable(args_mock, cfg)


class TestPromptForDependencyHandling:
    @pytest.mark.parametrize(
        [
            "service",
            "all_dependencies",
            "enabled_service_names",
            "called_name",
            "service_title",
            "cfg_block_disable_on_enable",
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
                        name="one", incompatible_with=[], depends_on=[]
                    )
                ],
                [],
                "one",
                "One",
                False,
                [],
                [],
                does_not_raise(),
            ),
            # incompatible with "two", but two not enabled
            (
                "one",
                [
                    ServiceWithDependencies(
                        name="one",
                        incompatible_with=[
                            ServiceWithReason(
                                name="two", reason=mock.MagicMock()
                            )
                        ],
                        depends_on=[],
                    )
                ],
                [],
                "one",
                "One",
                False,
                [],
                [],
                does_not_raise(),
            ),
            # incompatible with "two", two enabled, successful prompt
            (
                "one",
                [
                    ServiceWithDependencies(
                        name="one",
                        incompatible_with=[
                            ServiceWithReason(
                                name="two", reason=mock.MagicMock()
                            )
                        ],
                        depends_on=[],
                    )
                ],
                ["two"],
                "one",
                "One",
                False,
                [True],
                [mock.call(msg=mock.ANY)],
                does_not_raise(),
            ),
            # incompatible with "two", two enabled, cfg denies
            (
                "one",
                [
                    ServiceWithDependencies(
                        name="one",
                        incompatible_with=[
                            ServiceWithReason(
                                name="two", reason=mock.MagicMock()
                            )
                        ],
                        depends_on=[],
                    )
                ],
                ["two"],
                "one",
                "One",
                True,
                [],
                [],
                pytest.raises(exceptions.IncompatibleServiceStopsEnable),
            ),
            # incompatible with "two", two enabled, denied prompt
            (
                "one",
                [
                    ServiceWithDependencies(
                        name="one",
                        incompatible_with=[
                            ServiceWithReason(
                                name="two", reason=mock.MagicMock()
                            )
                        ],
                        depends_on=[],
                    )
                ],
                ["two"],
                "one",
                "One",
                False,
                [False],
                [mock.call(msg=mock.ANY)],
                pytest.raises(exceptions.IncompatibleServiceStopsEnable),
            ),
            # incompatible with "two" and "three", three enabled, success
            (
                "one",
                [
                    ServiceWithDependencies(
                        name="one",
                        incompatible_with=[
                            ServiceWithReason(
                                name="two", reason=mock.MagicMock()
                            ),
                            ServiceWithReason(
                                name="three", reason=mock.MagicMock()
                            ),
                        ],
                        depends_on=[],
                    )
                ],
                ["three"],
                "one",
                "One",
                False,
                [True],
                [mock.call(msg=mock.ANY)],
                does_not_raise(),
            ),
            # depends on "two", but two already enabled
            (
                "one",
                [
                    ServiceWithDependencies(
                        name="one",
                        incompatible_with=[],
                        depends_on=[
                            ServiceWithReason(
                                name="two", reason=mock.MagicMock()
                            )
                        ],
                    )
                ],
                ["two"],
                "one",
                "One",
                False,
                [],
                [],
                does_not_raise(),
            ),
            # depends on "two", two not enabled, successful prompt
            (
                "one",
                [
                    ServiceWithDependencies(
                        name="one",
                        incompatible_with=[],
                        depends_on=[
                            ServiceWithReason(
                                name="two", reason=mock.MagicMock()
                            )
                        ],
                    )
                ],
                [],
                "one",
                "One",
                False,
                [True],
                [mock.call(msg=mock.ANY)],
                does_not_raise(),
            ),
            # depends on "two", two not enabled, denied prompt
            (
                "one",
                [
                    ServiceWithDependencies(
                        name="one",
                        incompatible_with=[],
                        depends_on=[
                            ServiceWithReason(
                                name="two", reason=mock.MagicMock()
                            )
                        ],
                    )
                ],
                [],
                "one",
                "One",
                False,
                [False],
                [mock.call(msg=mock.ANY)],
                pytest.raises(exceptions.RequiredServiceStopsEnable),
            ),
            # depends on "two" and "three", three not enabled, success prompt
            (
                "one",
                [
                    ServiceWithDependencies(
                        name="one",
                        incompatible_with=[],
                        depends_on=[
                            ServiceWithReason(
                                name="two", reason=mock.MagicMock()
                            ),
                            ServiceWithReason(
                                name="three", reason=mock.MagicMock()
                            ),
                        ],
                    )
                ],
                ["two"],
                "one",
                "One",
                False,
                [True],
                [mock.call(msg=mock.ANY)],
                does_not_raise(),
            ),
            # lots of stuff
            (
                "one",
                [
                    ServiceWithDependencies(
                        name="one",
                        incompatible_with=[
                            ServiceWithReason(
                                name="two", reason=mock.MagicMock()
                            ),
                            ServiceWithReason(
                                name="three", reason=mock.MagicMock()
                            ),
                            ServiceWithReason(
                                name="four", reason=mock.MagicMock()
                            ),
                        ],
                        depends_on=[
                            ServiceWithReason(
                                name="five", reason=mock.MagicMock()
                            ),
                            ServiceWithReason(
                                name="six", reason=mock.MagicMock()
                            ),
                            ServiceWithReason(
                                name="seven", reason=mock.MagicMock()
                            ),
                        ],
                    )
                ],
                ["two", "four", "six"],
                "one",
                "One",
                False,
                [True, True, True, True],
                [
                    mock.call(msg=mock.ANY),
                    mock.call(msg=mock.ANY),
                    mock.call(msg=mock.ANY),
                    mock.call(msg=mock.ANY),
                ],
                does_not_raise(),
            ),
        ],
    )
    @mock.patch("uaclient.entitlements.get_title")
    @mock.patch("uaclient.util.prompt_for_confirmation")
    @mock.patch("uaclient.util.is_config_value_true")
    def test_prompt_for_dependency_handling(
        self,
        m_is_config_value_true,
        m_prompt_for_confirmation,
        m_entitlement_get_title,
        service,
        all_dependencies,
        enabled_service_names,
        called_name,
        service_title,
        cfg_block_disable_on_enable,
        prompt_side_effects,
        expected_prompts,
        expected_raise,
        FakeConfig,
    ):
        m_entitlement_get_title.side_effect = (
            lambda cfg, name, variant="": name.title()
        )
        m_is_config_value_true.return_value = cfg_block_disable_on_enable
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
