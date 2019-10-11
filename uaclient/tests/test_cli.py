import io
import logging
import mock
import os
import stat
import sys
import textwrap

import pytest

from uaclient.cli import (
    assert_attached,
    assert_root,
    get_parser,
    main,
    setup_logging,
)

from uaclient.exceptions import (
    NonRootUserError,
    UserFacingError,
    UnattachedError,
)
from uaclient.testing.fakes import FakeConfig


BIG_DESC = "123456789 " * 7 + "next line"
BIG_URL = "http://" + "adsf" * 10


SERVICES_WRAPPED_HELP = textwrap.dedent(
    """
Client to manage Ubuntu Advantage support services on a machine.
 - cc-eal: Common Criteria EAL2 Provisioning Packages
   (https://ubuntu.com/cc-eal)
 - cis-audit: Center for Internet Security Audit Tools
   (https://ubuntu.com/cis-audit)
 - esm-infra: UA Infra: Extended Security Maintenance (https://ubuntu.com/esm)
 - fips: NIST-certified FIPS modules (https://ubuntu.com/fips)
 - fips-updates: Uncertified security updates to FIPS modules
 - livepatch: Canonical Livepatch service (https://ubuntu.com/livepatch)
"""
)


class TestCLIParser:
    maxDiff = None

    @mock.patch("uaclient.cli.entitlements")
    def test_help_descr_and_url_is_wrapped_at_eighty_chars(
        self, m_entitlements
    ):
        """Help lines are wrapped at 80 chars"""

        def cls_mock_factory(desc, url):
            return mock.Mock(description=desc, help_doc_url=url)

        m_entitlements.ENTITLEMENT_CLASS_BY_NAME = {
            "test": cls_mock_factory(BIG_DESC, BIG_URL)
        }

        parser = get_parser()
        help_file = io.StringIO()
        parser.print_help(file=help_file)
        lines = [
            " - test: " + " ".join(["123456789"] * 7),
            "   next line ({url})".format(url=BIG_URL),
        ]
        assert "\n".join(lines) in help_file.getvalue()

    def test_help_sourced_dynamically_from_each_entitlement(self):
        """Help output is sourced from entitlement name and description."""
        parser = get_parser()
        help_file = io.StringIO()
        parser.print_help(file=help_file)
        assert SERVICES_WRAPPED_HELP in help_file.getvalue()


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
    def test_assert_attached_when_attached(self, capsys, uid):
        @assert_attached()
        def test_function(args, cfg):
            return mock.sentinel.success

        cfg = FakeConfig.for_attached_machine()

        with mock.patch("uaclient.cli.os.getuid", return_value=uid):
            ret = test_function(mock.Mock(), cfg)

        assert mock.sentinel.success == ret

        out, _err = capsys.readouterr()
        assert "" == out.strip()

    def test_assert_attached_when_unattached(self, uid):
        @assert_attached()
        def test_function(args, cfg):
            pass

        cfg = FakeConfig()

        with mock.patch("uaclient.cli.os.getuid", return_value=uid):
            with pytest.raises(UnattachedError):
                test_function(mock.Mock(), cfg)


class TestMain:
    @mock.patch("uaclient.cli.setup_logging")
    @mock.patch("uaclient.cli.get_parser")
    def test_keyboard_interrupt_handled_gracefully(
        self,
        m_get_parser,
        _m_setup_logging,
        capsys,
        logging_sandbox,
        caplog_text,
    ):
        m_args = m_get_parser.return_value.parse_args.return_value
        m_args.action.side_effect = KeyboardInterrupt

        with pytest.raises(SystemExit) as excinfo:
            main(["some", "args"])

        exc = excinfo.value
        assert 1 == exc.code

        out, err = capsys.readouterr()
        assert "" == out
        assert "Interrupt received; exiting.\n" == err
        error_log = caplog_text()
        assert "Traceback (most recent call last):" in error_log

    @pytest.mark.parametrize("caplog_text", [logging.ERROR], indirect=True)
    @mock.patch("uaclient.cli.setup_logging")
    @mock.patch("uaclient.cli.get_parser")
    def test_user_facing_error_handled_gracefully(
        self,
        m_get_parser,
        _m_setup_logging,
        capsys,
        logging_sandbox,
        caplog_text,
    ):
        msg = "You need to know about this."

        m_args = m_get_parser.return_value.parse_args.return_value
        m_args.action.side_effect = UserFacingError(msg)

        with pytest.raises(SystemExit) as excinfo:
            main(["some", "args"])

        exc = excinfo.value
        assert 1 == exc.code

        out, err = capsys.readouterr()
        assert "" == out
        assert "{}\n".format(msg) == err
        error_log = caplog_text()
        assert msg in error_log
        assert "Traceback (most recent call last):" in error_log


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
