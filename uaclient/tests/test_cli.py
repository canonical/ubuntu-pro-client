import contextlib
import io
import logging
import mock
import os
import socket
import stat
import sys
import textwrap

import pytest

from uaclient.cli import (
    action_help,
    assert_attached,
    assert_not_attached,
    assert_root,
    get_parser,
    main,
    get_valid_entitlement_names,
    setup_logging,
)

from uaclient.exceptions import (
    AlreadyAttachedError,
    NonRootUserError,
    UserFacingError,
    UnattachedError,
)
from uaclient import status
from uaclient import util


BIG_DESC = "123456789 " * 7 + "next line"
BIG_URL = "http://" + "adsf" * 10


SERVICES_WRAPPED_HELP = textwrap.dedent(
    """
Client to manage Ubuntu Advantage services on a machine.
 - cc-eal: Common Criteria EAL2 Provisioning Packages
   (https://ubuntu.com/cc-eal)
 - cis-audit: Center for Internet Security Audit Tools
   (https://ubuntu.com/cis-audit)
 - esm-apps: UA Apps: Extended Security Maintenance (https://ubuntu.com/esm)
 - esm-infra: UA Infra: Extended Security Maintenance (https://ubuntu.com/esm)
 - fips: NIST-certified FIPS modules (https://ubuntu.com/fips)
 - fips-updates: Uncertified security updates to FIPS modules
 - livepatch: Canonical Livepatch service (https://ubuntu.com/livepatch)
"""
)


@pytest.fixture(params=["direct", "--help", "ua help"])
def get_help(request, capsys):
    if request.param == "direct":

        def _get_help_output():
            parser = get_parser()
            help_file = io.StringIO()
            parser.print_help(file=help_file)
            return help_file.getvalue()

    elif request.param == "--help":

        def _get_help_output():
            parser = get_parser()
            with mock.patch("sys.argv", ["ua", "--help"]):
                with pytest.raises(SystemExit):
                    parser.parse_args()
            out, _err = capsys.readouterr()
            return out

    elif request.param == "ua help":

        def _get_help_output():
            with mock.patch("sys.argv", ["ua", "help"]):
                main()
            out, _err = capsys.readouterr()
            return out

    else:
        raise NotImplementedError("Unknown help source: {}", request.param)
    return _get_help_output


class TestCLIParser:
    maxDiff = None

    @mock.patch("uaclient.cli.entitlements")
    def test_help_descr_and_url_is_wrapped_at_eighty_chars(
        self, m_entitlements, get_help
    ):
        """Help lines are wrapped at 80 chars"""

        def cls_mock_factory(desc, url):
            return mock.Mock(description=desc, help_doc_url=url)

        m_entitlements.ENTITLEMENT_CLASS_BY_NAME = {
            "test": cls_mock_factory(BIG_DESC, BIG_URL)
        }

        lines = [
            " - test: " + " ".join(["123456789"] * 7),
            "   next line ({url})".format(url=BIG_URL),
        ]
        assert "\n".join(lines) in get_help()

    def test_help_sourced_dynamically_from_each_entitlement(self, get_help):
        """Help output is sourced from entitlement name and description."""
        assert SERVICES_WRAPPED_HELP in get_help()

    @mock.patch("uaclient.contract.get_available_resources")
    @mock.patch(
        "uaclient.config.UAConfig.is_attached", new_callable=mock.PropertyMock
    )
    def test_help_command_when_unnatached(
        self, m_attached, m_available_resources
    ):
        """Test help command when a service is provided."""
        import uaclient.entitlements as ent

        m_args = mock.MagicMock()
        m_name = mock.PropertyMock(return_value="test")
        type(m_args).name = m_name

        m_entitlement_cls = mock.MagicMock()
        m_ent_help_info = mock.PropertyMock(return_value="Test service")
        type(m_entitlement_cls).help_info = m_ent_help_info

        m_attached.return_value = False

        m_available_resources.return_value = [
            {"name": "test", "available": True}
        ]

        expected_msg = "\n".join(
            ["name: test", "available: yes", "help: Test service"]
        )

        fake_stdout = io.StringIO()
        with mock.patch.object(
            ent, "ENTITLEMENT_CLASS_BY_NAME", {"test": m_entitlement_cls}
        ):
            with contextlib.redirect_stdout(fake_stdout):
                action_help(m_args, None)

        assert expected_msg.strip() == fake_stdout.getvalue().strip()

    @mock.patch("uaclient.contract.get_available_resources")
    @mock.patch(
        "uaclient.config.UAConfig.is_attached", new_callable=mock.PropertyMock
    )
    def test_help_command_when_attached(
        self, m_attached, m_available_resources
    ):
        """Test help command when a service is provided."""
        import uaclient.entitlements as ent

        m_args = mock.MagicMock()
        m_name = mock.PropertyMock(return_value="test")
        type(m_args).name = m_name

        m_entitlement_cls = mock.MagicMock()
        m_ent_help_info = mock.PropertyMock(return_value="Test service")
        type(m_entitlement_cls).help_info = m_ent_help_info
        m_entitlement_obj = m_entitlement_cls.return_value

        status_ret = status.ContractStatus.ENTITLED
        m_entitlement_obj.contract_status.return_value = status_ret
        m_entitlement_obj.user_facing_status.return_value = (
            status.UserFacingStatus.ACTIVE,
            "active",
        )
        m_ent_name = mock.PropertyMock(return_value="test")
        type(m_entitlement_obj).name = m_ent_name
        m_ent_desc = mock.PropertyMock(return_value="description")
        type(m_entitlement_obj).description = m_ent_desc

        m_attached.return_value = True
        m_available_resources.return_value = [
            {"name": "test", "available": True}
        ]

        expected_msg = "\n".join(
            [
                "name: test",
                "entitled: yes",
                "status: enabled",
                "help: Test service",
            ]
        )

        fake_stdout = io.StringIO()
        with mock.patch.object(
            ent, "ENTITLEMENT_CLASS_BY_NAME", {"test": m_entitlement_cls}
        ):
            with contextlib.redirect_stdout(fake_stdout):
                action_help(m_args, None)

        assert expected_msg.strip() == fake_stdout.getvalue().strip()


class TestAssertRoot:
    def test_assert_root_when_root(self):
        arg, kwarg = mock.sentinel.arg, mock.sentinel.kwarg

        @assert_root
        def test_function(arg, *, kwarg):
            assert arg == mock.sentinel.arg
            assert kwarg == mock.sentinel.kwarg

            return mock.sentinel.success

        with mock.patch("uaclient.cli.os.getuid", return_value=0):
            ret = test_function(arg, kwarg=kwarg)

        assert mock.sentinel.success == ret

    def test_assert_root_when_not_root(self):
        @assert_root
        def test_function():
            pass

        with mock.patch("uaclient.cli.os.getuid", return_value=1000):
            with pytest.raises(NonRootUserError):
                test_function()


# Test multiple uids, to be sure that the root checking is absent
@pytest.mark.parametrize("uid", [0, 1000])
class TestAssertAttached:
    def test_assert_attached_when_attached(self, capsys, uid, FakeConfig):
        @assert_attached()
        def test_function(args, cfg):
            return mock.sentinel.success

        cfg = FakeConfig.for_attached_machine()

        with mock.patch("uaclient.cli.os.getuid", return_value=uid):
            ret = test_function(mock.Mock(), cfg)

        assert mock.sentinel.success == ret

        out, _err = capsys.readouterr()
        assert "" == out.strip()

    def test_assert_attached_when_unattached(self, uid, FakeConfig):
        @assert_attached()
        def test_function(args, cfg):
            pass

        cfg = FakeConfig()

        with mock.patch("uaclient.cli.os.getuid", return_value=uid):
            with pytest.raises(UnattachedError):
                test_function(mock.Mock(), cfg)


@pytest.mark.parametrize("uid", [0, 1000])
class TestAssertNotAttached:
    def test_when_attached(self, uid, FakeConfig):
        @assert_not_attached
        def test_function(args, cfg):
            pass

        cfg = FakeConfig.for_attached_machine()

        with mock.patch("uaclient.cli.os.getuid", return_value=uid):
            with pytest.raises(AlreadyAttachedError):
                test_function(mock.Mock(), cfg)

    def test_when_not_attached(self, capsys, uid, FakeConfig):
        @assert_not_attached
        def test_function(args, cfg):
            return mock.sentinel.success

        cfg = FakeConfig()

        with mock.patch("uaclient.cli.os.getuid", return_value=uid):
            ret = test_function(mock.Mock(), cfg)

        assert mock.sentinel.success == ret

        out, _err = capsys.readouterr()
        assert "" == out.strip()


class TestMain:
    @pytest.mark.parametrize(
        "exception,expected_error_msg,expected_log",
        (
            (
                KeyboardInterrupt,
                "Interrupt received; exiting.\n",
                "KeyboardInterrupt",
            ),
            (
                TypeError("'NoneType' object is not subscriptable"),
                status.MESSAGE_UNEXPECTED_ERROR + "\n",
                "Unhandled exception, please file a bug",
            ),
        ),
    )
    @mock.patch("uaclient.cli.setup_logging")
    @mock.patch("uaclient.cli.get_parser")
    def test_errors_handled_gracefully(
        self,
        m_get_parser,
        _m_setup_logging,
        capsys,
        logging_sandbox,
        caplog_text,
        exception,
        expected_error_msg,
        expected_log,
    ):
        m_args = m_get_parser.return_value.parse_args.return_value
        m_args.action.side_effect = exception

        with pytest.raises(SystemExit) as excinfo:
            with mock.patch("sys.argv", ["/usr/bin/ua", "subcmd"]):
                main()

        exc = excinfo.value
        assert 1 == exc.code

        out, err = capsys.readouterr()
        assert "" == out
        assert expected_error_msg == err
        error_log = caplog_text()
        assert "Traceback (most recent call last):" in error_log
        assert expected_log in error_log

    @pytest.mark.parametrize(
        "exception,expected_exit_code",
        [
            (UserFacingError("You need to know about this."), 1),
            (AlreadyAttachedError(mock.MagicMock()), 0),
        ],
    )
    @mock.patch("uaclient.cli.setup_logging")
    @mock.patch("uaclient.cli.get_parser")
    def test_user_facing_error_handled_gracefully(
        self,
        m_get_parser,
        _m_setup_logging,
        capsys,
        logging_sandbox,
        caplog_text,
        exception,
        expected_exit_code,
    ):
        m_args = m_get_parser.return_value.parse_args.return_value
        m_args.action.side_effect = exception
        expected_msg = exception.msg

        with pytest.raises(SystemExit) as excinfo:
            main(["some", "args"])

        exc = excinfo.value
        assert expected_exit_code == exc.code

        out, err = capsys.readouterr()
        assert "" == out
        assert "{}\n".format(expected_msg) == err
        error_log = caplog_text()
        # pytest 4.6.x started indenting trailing lines in log messages, which
        # meant that our matching here stopped working once we introduced
        # newlines into this log output in #973.  (If focal moves onto pytest
        # 5.x before release, then we can remove this workaround.)  The
        # upstream issue is https://github.com/pytest-dev/pytest/issues/5515
        error_log = "\n".join(
            [line.strip() for line in error_log.splitlines()]
        )
        assert expected_msg in error_log
        assert "Traceback (most recent call last):" in error_log

    @pytest.mark.parametrize(
        "error_url,expected_log",
        (
            (
                None,
                "Check your Internet connection and try again."
                " [Errno -2] Name or service not known",
            ),
            (
                "http://nowhere.com",
                "Check your Internet connection and try again."
                " Failed to access URL: http://nowhere.com."
                " [Errno -2] Name or service not known",
            ),
        ),
    )
    @mock.patch("uaclient.cli.setup_logging")
    @mock.patch("uaclient.cli.get_parser")
    def test_url_error_handled_gracefully(
        self,
        m_get_parser,
        _m_setup_logging,
        error_url,
        expected_log,
        capsys,
        logging_sandbox,
        caplog_text,
    ):

        m_args = m_get_parser.return_value.parse_args.return_value
        m_args.action.side_effect = util.UrlError(
            socket.gaierror(-2, "Name or service not known"), url=error_url
        )

        with pytest.raises(SystemExit) as excinfo:
            main(["some", "args"])

        exc = excinfo.value
        assert 1 == exc.code

        out, err = capsys.readouterr()
        assert "" == out
        assert "{}\n".format(status.MESSAGE_CONNECTIVITY_ERROR) == err
        error_log = caplog_text()

        assert expected_log in error_log
        assert "Traceback (most recent call last):" in error_log

    @pytest.mark.parametrize("caplog_text", [logging.DEBUG], indirect=True)
    @mock.patch("uaclient.cli.setup_logging")
    @mock.patch("uaclient.cli.get_parser")
    def test_command_line_is_logged(
        self, _m_get_parser, _m_setup_logging, logging_sandbox, caplog_text
    ):
        main(["some", "args"])

        log = caplog_text()

        assert "['some', 'args']" in log


class TestSetupLogging:
    @pytest.mark.parametrize("level", (logging.INFO, logging.ERROR))
    def test_console_log_configured_if_not_present(
        self, level, capsys, logging_sandbox
    ):
        setup_logging(level, logging.INFO)
        logging.log(level, "after setup")
        logging.log(level - 1, "not present")

        _, err = capsys.readouterr()
        assert "after setup" in err
        assert "not present" not in err

    def test_console_log_configured_if_already_present(
        self, capsys, logging_sandbox
    ):
        logging.getLogger().addHandler(logging.StreamHandler(sys.stderr))

        logging.error("before setup")
        setup_logging(logging.INFO, logging.INFO)
        logging.error("after setup")

        # 'before setup' will be in stderr, so check that setup_logging
        # configures the format
        _, err = capsys.readouterr()
        assert "ERROR: before setup" not in err
        assert "ERROR: after setup" in err

    @mock.patch("uaclient.cli.os.getuid", return_value=100)
    def test_file_log_not_configured_if_not_root(
        self, m_getuid, tmpdir, logging_sandbox
    ):
        log_file = tmpdir.join("log_file")

        setup_logging(logging.INFO, logging.INFO, log_file=log_file.strpath)
        logging.info("after setup")

        assert not log_file.exists()

    @pytest.mark.parametrize("log_filename", (None, "file.log"))
    @mock.patch("uaclient.cli.os.getuid", return_value=0)
    @mock.patch("uaclient.cli.config")
    def test_file_log_configured_if_root(
        self, m_config, _m_getuid, log_filename, logging_sandbox, tmpdir
    ):
        if log_filename is None:
            log_filename = "default.log"
            log_file = tmpdir.join(log_filename)
            m_config.CONFIG_DEFAULTS = {"log_file": log_file.strpath}
        else:
            log_file = tmpdir.join(log_filename)

        setup_logging(logging.INFO, logging.INFO, log_file=log_file.strpath)
        logging.info("after setup")

        assert "after setup" in log_file.read()

    @pytest.mark.parametrize("pre_existing", (True, False))
    @mock.patch("uaclient.cli.os.getuid", return_value=0)
    @mock.patch("uaclient.cli.config")
    def test_file_log_only_readable_by_root(
        self, m_config, _m_getuid, logging_sandbox, tmpdir, pre_existing
    ):
        log_file = tmpdir.join("root-only.log")
        log_path = log_file.strpath

        if pre_existing:
            log_file.write("existing content\n")
            assert 0o600 != stat.S_IMODE(os.lstat(log_path).st_mode)

        setup_logging(logging.INFO, logging.INFO, log_file=log_path)
        logging.info("after setup")

        assert 0o600 == stat.S_IMODE(os.lstat(log_path).st_mode)
        log_content = log_file.read()
        assert "after setup" in log_content
        if pre_existing:
            assert "existing content" in log_content


class TestGetValidEntitlementNames:
    @mock.patch("uaclient.cli.entitlements")
    def test_get_valid_entitlements(self, m_entitlements):
        m_entitlements.ENTITLEMENT_CLASS_BY_NAME = {
            "ent1": True,
            "ent2": True,
            "ent3": True,
        }

        names = ["ent1", "ent3", "ent4"]
        expected_ents_found = ["ent1", "ent3"]
        expected_ents_not_found = ["ent4"]

        actual_ents_found, actual_ents_not_found = get_valid_entitlement_names(
            names
        )

        assert expected_ents_found == actual_ents_found
        assert expected_ents_not_found == actual_ents_not_found
