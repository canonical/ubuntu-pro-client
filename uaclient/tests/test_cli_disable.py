import contextlib
import io
import json
import textwrap

import mock
import pytest

from uaclient import entitlements, event_logger, exceptions, status
from uaclient.cli import action_disable, main, main_error_handler

ALL_SERVICE_MSG = "\n".join(
    textwrap.wrap(
        "Try " + ", ".join(entitlements.valid_services(allow_beta=True)) + ".",
        width=80,
        break_long_words=False,
        break_on_hyphens=False,
    )
)

HELP_OUTPUT = textwrap.dedent(
    """\
usage: ua disable <service> [<service>] [flags]

Disable an Ubuntu Advantage service.

Arguments:
  service              the name(s) of the Ubuntu Advantage services to disable
                       One of: cc-eal, cis, esm-infra, fips, fips-updates,
                       livepatch

Flags:
  -h, --help           show this help message and exit
  --assume-yes         do not prompt for confirmation before performing the
                       disable
  --format {cli,json}  output disable in the specified format (default: cli)
"""
)


@mock.patch("uaclient.cli.os.getuid", return_value=0)
class TestDisable:
    @mock.patch("uaclient.cli.contract.get_available_resources")
    def test_disable_help(self, _m_resources, _getuid, capsys):
        with pytest.raises(SystemExit):
            with mock.patch("sys.argv", ["/usr/bin/ua", "disable", "--help"]):
                main()
        out, _err = capsys.readouterr()
        assert HELP_OUTPUT == out

    @pytest.mark.parametrize("service", [["testitlement"], ["ent1", "ent2"]])
    @pytest.mark.parametrize("assume_yes", (True, False))
    @pytest.mark.parametrize(
        "disable_return,return_code", ((True, 0), (False, 1))
    )
    @mock.patch("uaclient.cli.entitlements.entitlement_factory")
    @mock.patch("uaclient.cli.entitlements.valid_services")
    def test_entitlement_instantiated_and_disabled(
        self,
        m_valid_services,
        m_entitlement_factory,
        _m_getuid,
        disable_return,
        return_code,
        assume_yes,
        service,
        tmpdir,
        capsys,
        event,
    ):
        entitlements_cls = []
        entitlements_obj = []
        ent_dict = {}
        m_valid_services.return_value = []

        if not disable_return:
            fail = status.CanDisableFailure(
                status.CanDisableFailureReason.ALREADY_DISABLED, message="test"
            )
        else:
            fail = None

        for entitlement_name in service:
            m_entitlement_cls = mock.Mock()

            m_entitlement = m_entitlement_cls.return_value
            m_entitlement.disable.return_value = (disable_return, fail)

            entitlements_obj.append(m_entitlement)
            entitlements_cls.append(m_entitlement_cls)
            m_valid_services.return_value.append(entitlement_name)
            ent_dict[entitlement_name] = m_entitlement_cls
            type(m_entitlement).name = mock.PropertyMock(
                return_value=entitlement_name
            )

        def factory_side_effect(name, ent_dict=ent_dict):
            return ent_dict.get(name)

        m_entitlement_factory.side_effect = factory_side_effect

        m_cfg = mock.Mock()
        m_cfg.check_lock_info.return_value = (-1, "")
        m_cfg.data_path.return_value = tmpdir.join("lock").strpath

        args_mock = mock.Mock()
        args_mock.service = service
        args_mock.assume_yes = assume_yes

        ret = action_disable(args_mock, cfg=m_cfg)

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

        args_mock.assume_yes = True
        args_mock.format = "json"
        with mock.patch.object(
            event,
            "_event_logger_mode",
            event_logger.EventLoggerMode.MACHINE_READABLE,
        ):
            with mock.patch.object(event, "set_event_mode"):
                fake_stdout = io.StringIO()
                with contextlib.redirect_stdout(fake_stdout):
                    ret = action_disable(args_mock, cfg=m_cfg)

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
                    "message": fail.message,
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
    def test_entitlements_not_found_disabled_and_enabled(
        self,
        m_valid_services,
        m_entitlement_factory,
        _m_getuid,
        assume_yes,
        tmpdir,
        event,
    ):
        expected_error_tmpl = status.MESSAGE_INVALID_SERVICE_OP_FAILURE_TMPL
        num_calls = 2

        m_ent1_cls = mock.Mock()
        m_ent1_obj = m_ent1_cls.return_value
        m_ent1_obj.disable.return_value = (
            False,
            status.CanDisableFailure(
                status.CanDisableFailureReason.ALREADY_DISABLED, message="test"
            ),
        )
        type(m_ent1_obj).name = mock.PropertyMock(return_value="ent1")

        m_ent2_cls = mock.Mock()
        m_ent2_obj = m_ent2_cls.return_value
        m_ent2_obj.disable.return_value = (
            False,
            status.CanDisableFailure(
                status.CanDisableFailureReason.ALREADY_DISABLED, message="test"
            ),
        )
        type(m_ent2_obj).name = mock.PropertyMock(return_value="ent2")

        m_ent3_cls = mock.Mock()
        m_ent3_obj = m_ent3_cls.return_value
        m_ent3_obj.disable.return_value = (True, None)
        type(m_ent3_obj).name = mock.PropertyMock(return_value="ent3")

        def factory_side_effect(name):
            if name == "ent2":
                return m_ent2_cls
            if name == "ent3":
                return m_ent3_cls
            return None

        m_entitlement_factory.side_effect = factory_side_effect
        m_valid_services.return_value = ["ent2", "ent3"]

        m_cfg = mock.Mock()
        m_cfg.check_lock_info.return_value = (-1, "")
        m_cfg.data_path.return_value = tmpdir.join("lock").strpath
        args_mock = mock.Mock()
        args_mock.service = ["ent1", "ent2", "ent3"]
        args_mock.assume_yes = assume_yes

        with pytest.raises(exceptions.UserFacingError) as err:
            action_disable(args_mock, cfg=m_cfg)

        assert (
            expected_error_tmpl.format(
                operation="disable", name="ent1", service_msg="Try ent2, ent3."
            )
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

        args_mock.assume_yes = True
        args_mock.format = "json"
        with pytest.raises(SystemExit):
            with mock.patch.object(
                event,
                "_event_logger_mode",
                event_logger.EventLoggerMode.MACHINE_READABLE,
            ):
                with mock.patch.object(event, "set_event_mode"):
                    fake_stdout = io.StringIO()
                    with contextlib.redirect_stdout(fake_stdout):
                        main_error_handler(action_disable)(args_mock, m_cfg)

        expected = {
            "_schema_version": event_logger.JSON_SCHEMA_VERSION,
            "result": "failure",
            "errors": [
                {"message": "test", "service": "ent2", "type": "service"},
                {
                    "message": (
                        "Cannot disable unknown service 'ent1'.\n"
                        "Try ent2, ent3."
                    ),
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
        "uid,expected_error_template",
        [
            (0, status.MESSAGE_INVALID_SERVICE_OP_FAILURE_TMPL),
            (1000, status.MESSAGE_NONROOT_USER),
        ],
    )
    def test_invalid_service_error_message(
        self, m_getuid, uid, expected_error_template, FakeConfig, event
    ):
        """Check invalid service name results in custom error message."""
        m_getuid.return_value = uid

        cfg = FakeConfig.for_attached_machine()
        args = mock.MagicMock()
        expected_error = expected_error_template.format(
            operation="disable", name="bogus", service_msg=ALL_SERVICE_MSG
        )
        with pytest.raises(exceptions.UserFacingError) as err:
            args.service = ["bogus"]
            action_disable(args, cfg)
        assert expected_error == err.value.msg

        args.assume_yes = True
        args.format = "json"
        with pytest.raises(SystemExit):
            with mock.patch.object(
                event,
                "_event_logger_mode",
                event_logger.EventLoggerMode.MACHINE_READABLE,
            ):
                with mock.patch.object(event, "set_event_mode"):
                    fake_stdout = io.StringIO()
                    with contextlib.redirect_stdout(fake_stdout):
                        main_error_handler(action_disable)(args, cfg)

        expected = {
            "_schema_version": event_logger.JSON_SCHEMA_VERSION,
            "result": "failure",
            "errors": [
                {"message": expected_error, "service": None, "type": "system"}
            ],
            "failed_services": [],
            "needs_reboot": False,
            "processed_services": [],
            "warnings": [],
        }
        assert expected == json.loads(fake_stdout.getvalue())

    @pytest.mark.parametrize("service", [["bogus"], ["bogus1", "bogus2"]])
    def test_invalid_service_names(self, m_getuid, service, FakeConfig, event):
        m_getuid.return_value = 0
        expected_error_tmpl = status.MESSAGE_INVALID_SERVICE_OP_FAILURE_TMPL

        cfg = FakeConfig.for_attached_machine()
        args = mock.MagicMock()
        expected_error = expected_error_tmpl.format(
            operation="disable",
            name=", ".join(sorted(service)),
            service_msg=ALL_SERVICE_MSG,
        )
        with pytest.raises(exceptions.UserFacingError) as err:
            args.service = service
            action_disable(args, cfg)

        assert expected_error == err.value.msg

        args.assume_yes = True
        args.format = "json"
        with pytest.raises(SystemExit):
            with mock.patch.object(
                event,
                "_event_logger_mode",
                event_logger.EventLoggerMode.MACHINE_READABLE,
            ):
                with mock.patch.object(event, "set_event_mode"):
                    fake_stdout = io.StringIO()
                    with contextlib.redirect_stdout(fake_stdout):
                        main_error_handler(action_disable)(args, cfg)

        expected = {
            "_schema_version": event_logger.JSON_SCHEMA_VERSION,
            "result": "failure",
            "errors": [
                {"message": expected_error, "service": None, "type": "system"}
            ],
            "failed_services": [],
            "needs_reboot": False,
            "processed_services": [],
            "warnings": [],
        }
        assert expected == json.loads(fake_stdout.getvalue())

    @pytest.mark.parametrize(
        "uid,expected_error_template",
        [
            (0, status.MESSAGE_ENABLE_FAILURE_UNATTACHED_TMPL),
            (1000, status.MESSAGE_NONROOT_USER),
        ],
    )
    def test_unattached_error_message(
        self, m_getuid, uid, expected_error_template, FakeConfig, event
    ):
        """Check that root user gets unattached message."""
        m_getuid.return_value = uid

        cfg = FakeConfig()
        args = mock.MagicMock()
        expected_error = expected_error_template.format(name="esm-infra")
        with pytest.raises(exceptions.UserFacingError) as err:
            args.service = ["esm-infra"]
            action_disable(args, cfg)

        assert expected_error == err.value.msg

        args.assume_yes = True
        args.format = "json"
        with pytest.raises(SystemExit):
            with mock.patch.object(
                event,
                "_event_logger_mode",
                event_logger.EventLoggerMode.MACHINE_READABLE,
            ):
                with mock.patch.object(event, "set_event_mode"):
                    fake_stdout = io.StringIO()
                    with contextlib.redirect_stdout(fake_stdout):
                        main_error_handler(action_disable)(args, cfg)

        expected = {
            "_schema_version": event_logger.JSON_SCHEMA_VERSION,
            "result": "failure",
            "errors": [
                {"message": expected_error, "service": None, "type": "system"}
            ],
            "failed_services": [],
            "needs_reboot": False,
            "processed_services": [],
            "warnings": [],
        }
        assert expected == json.loads(fake_stdout.getvalue())

    @mock.patch("uaclient.cli.util.subp")
    def test_lock_file_exists(self, m_subp, m_getuid, FakeConfig, event):
        """Check inability to disable if operation in progress holds lock."""
        cfg = FakeConfig().for_attached_machine()
        args = mock.MagicMock()
        expected_error = (
            "Unable to perform: ua disable.\n"
            "Operation in progress: ua enable (pid:123)"
        )
        with open(cfg.data_path("lock"), "w") as stream:
            stream.write("123:ua enable")
        with pytest.raises(exceptions.LockHeldError) as err:
            args.service = ["esm-infra"]
            action_disable(args, cfg)
        assert [mock.call(["ps", "123"])] == m_subp.call_args_list
        assert expected_error == err.value.msg

        args.assume_yes = True
        args.format = "json"
        with pytest.raises(SystemExit):
            with mock.patch.object(
                event,
                "_event_logger_mode",
                event_logger.EventLoggerMode.MACHINE_READABLE,
            ):
                with mock.patch.object(event, "set_event_mode"):
                    fake_stdout = io.StringIO()
                    with contextlib.redirect_stdout(fake_stdout):
                        main_error_handler(action_disable)(args, cfg)

        expected = {
            "_schema_version": event_logger.JSON_SCHEMA_VERSION,
            "result": "failure",
            "errors": [
                {"message": expected_error, "service": None, "type": "system"}
            ],
            "failed_services": [],
            "needs_reboot": False,
            "processed_services": [],
            "warnings": [],
        }
        assert expected == json.loads(fake_stdout.getvalue())
