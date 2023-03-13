import json
import logging
import os
import re
import stat
import sys
from io import StringIO

import mock
import pytest

from uaclient import log as pro_log

LOG = logging.getLogger(__name__)
LOG_FMT = "%(asctime)s%(name)s%(funcName)s%(lineno)s\
%(levelname)s%(message)s%(extra)s"
DATE_FMT = "%Y-%m-%dT%H:%M:%S%z"


class TestLogger:
    @pytest.mark.parametrize("caplog_text", [logging.INFO], indirect=True)
    def test_unredacted_text(self, caplog_text):
        text = "Bearer SEKRET"
        LOG.info(text)
        log = caplog_text()
        assert text in log

    @pytest.mark.parametrize(
        "raw_log,expected",
        (
            ("Super valuable", "Super valuable"),
            (
                "Hi 'Bearer not the droids you are looking for', data",
                "Hi 'Bearer <REDACTED>', data",
            ),
            (
                "Hi 'Bearer not the droids you are looking for', data",
                "Hi 'Bearer <REDACTED>', data",
            ),
            (
                "Executed with sys.argv: ['/usr/bin/ua', 'attach', 'SEKRET']",
                "Executed with sys.argv:"
                " ['/usr/bin/ua', 'attach', '<REDACTED>']",
            ),
            (
                "'resourceTokens': [{'token': 'SEKRET', 'type': 'cc-eal'}]'",
                "'resourceTokens':"
                " [{'token': '<REDACTED>', 'type': 'cc-eal'}]'",
            ),
            (
                "'machineToken': 'SEKRET', 'machineTokenInfo': 'blah'",
                "'machineToken': '<REDACTED>', 'machineTokenInfo': 'blah'",
            ),
            (
                "Failed running command '/usr/lib/apt/apt-helper download-file"
                "https://bearer:S3-Kr3T@esm.ubuntu.com/infra/ubuntu/pool/ "
                "[exit(100)]. Message: Download of file failed"
                " pkgAcquire::Run (13: Permission denied)",
                "Failed running command '/usr/lib/apt/apt-helper download-file"
                "https://bearer:<REDACTED>@esm.ubuntu.com/infra/ubuntu/pool/ "
                "[exit(100)]. Message: Download of file failed"
                " pkgAcquire::Run (13: Permission denied)",
            ),
            (
                "/snap/bin/canonical-livepatch enable S3-Kr3T, foobar",
                "/snap/bin/canonical-livepatch enable <REDACTED> foobar",
            ),
            (
                "Contract value for 'resourceToken' changed to S3kR3T",
                "Contract value for 'resourceToken' changed to <REDACTED>",
            ),
            (
                "data: {'contractToken': 'SEKRET', "
                "'contractTokenInfo':{'expiry'}}",
                "data: {'contractToken': '<REDACTED>', "
                "'contractTokenInfo':{'expiry'}}",
            ),
            (
                "data: {'resourceToken': 'SEKRET', "
                "'entitlement': {'affordances':'blah blah' }}",
                "data: {'resourceToken': '<REDACTED>', "
                "'entitlement': {'affordances':'blah blah' }}",
            ),
            (
                "https://contracts.canonical.com/v1/resources/livepatch"
                "?token=SEKRET: invalid token",
                "https://contracts.canonical.com/v1/resources/livepatch"
                "?token=<REDACTED> invalid token",
            ),
            (
                'data: {"identityToken": "SEket.124-_ys"}',
                'data: {"identityToken": "<REDACTED>"}',
            ),
            (
                "http://metadata/computeMetadata/v1/instance/service-accounts/"
                "default/identity?audience=contracts.canon, data: none",
                "http://metadata/computeMetadata/v1/instance/service-accounts/"
                "default/identity?audience=contracts.canon, data: none",
            ),
            (
                "response: "
                "http://metadata/computeMetadata/v1/instance/service-accounts/"
                "default/identity?audience=contracts.canon, data: none",
                "response: "
                "http://metadata/computeMetadata/v1/instance/service-accounts/"
                "default/identity?audience=contracts.canon, data: <REDACTED>",
            ),
            (
                "'token': 'SEKRET'",
                "'token': '<REDACTED>'",
            ),
            (
                "'userCode': 'SEKRET'",
                "'userCode': '<REDACTED>'",
            ),
            (
                "'magic_token=SEKRET'",
                "'magic_token=<REDACTED>'",
            ),
        ),
    )
    @pytest.mark.parametrize("caplog_text", [logging.INFO], indirect=True)
    def test_redacted_text(self, caplog_text, raw_log, expected):
        LOG.addFilter(pro_log.RedactionFilter())
        LOG.info(raw_log)
        log = caplog_text()
        assert expected in log


class TestLoggerFormatter:
    @pytest.mark.parametrize(
        "message,level,log_fn,levelname,extra",
        (
            ("mIDValue", logging.DEBUG, LOG.debug, "DEBUG", None),
            ("2B||~2B", logging.INFO, LOG.info, "INFO", None),
            (
                "2B||~2B",
                logging.WARNING,
                LOG.warning,
                "WARNING",
                {"key": "value"},
            ),
        ),
    )
    @pytest.mark.parametrize("caplog_text", [logging.NOTSET], indirect=True)
    def test_valid_json_output(
        self, caplog_text, message, level, log_fn, levelname, extra
    ):
        formatter = pro_log.JsonArrayFormatter(LOG_FMT, DATE_FMT)
        buffer = StringIO()
        sh = logging.StreamHandler(buffer)
        sh.setLevel(level)
        sh.setFormatter(formatter)
        LOG.addHandler(sh)
        log_fn(message, extra={"extra": extra})
        logged_value = buffer.getvalue()
        val = json.loads(logged_value)
        assert val[1] == levelname
        assert val[2] == __name__
        assert val[5] == message
        if extra:
            assert val[6].get("key") == extra.get("key")
        else:
            assert 7 == len(val)


class TestSetupLogging:
    @pytest.mark.parametrize("level", (logging.INFO, logging.ERROR))
    @mock.patch("uaclient.cli.util.we_are_currently_root", return_value=False)
    def test_console_log_configured_if_not_present(
        self, m_we_are_currently_root, level, capsys, logging_sandbox
    ):
        pro_log.setup_logging(level, logging.INFO)
        logging.log(level, "after setup")
        logging.log(level - 1, "not present")

        _, err = capsys.readouterr()
        assert "after setup" in err
        assert "not present" not in err

    @mock.patch("uaclient.cli.util.we_are_currently_root", return_value=False)
    def test_console_log_configured_if_already_present(
        self, m_we_are_currently_root, capsys, logging_sandbox
    ):
        logging.getLogger().addHandler(logging.StreamHandler(sys.stderr))

        logging.error("before setup")
        pro_log.setup_logging(logging.INFO, logging.INFO)
        logging.error("after setup")

        # 'before setup' will be in stderr, so check that setup_logging
        # configures the format
        _, err = capsys.readouterr()
        assert "ERROR: before setup" not in err
        assert "ERROR: after setup" in err

    @mock.patch("uaclient.cli.util.we_are_currently_root", return_value=False)
    def test_file_log_not_configured_if_not_root(
        self, m_we_are_currently_root, tmpdir, logging_sandbox
    ):
        log_file = tmpdir.join("log_file")

        pro_log.setup_logging(
            logging.INFO, logging.INFO, log_file=log_file.strpath
        )
        logging.info("after setup")

        assert not log_file.exists()

    @pytest.mark.parametrize("log_filename", (None, "file.log"))
    @mock.patch("uaclient.cli.config")
    def test_file_log_configured_if_root(
        self,
        m_config,
        log_filename,
        logging_sandbox,
        tmpdir,
    ):
        if log_filename is None:
            log_filename = "default.log"
            log_file = tmpdir.join(log_filename)
            m_config.CONFIG_DEFAULTS = {"log_file": log_file.strpath}
        else:
            log_file = tmpdir.join(log_filename)

        pro_log.setup_logging(
            logging.INFO, logging.INFO, log_file=log_file.strpath
        )
        logging.info("after setup")

        assert "after setup" in log_file.read()

    def test_file_log_configured_if_already_present(
        self,
        logging_sandbox,
        tmpdir,
    ):
        some_file = tmpdir.join("default.log")
        logging.getLogger().addHandler(logging.FileHandler(some_file.strpath))

        log_file = tmpdir.join("file.log")

        logging.error("before setup")
        pro_log.setup_logging(
            logging.INFO, logging.INFO, log_file=log_file.strpath
        )
        logging.error("after setup")

        content = log_file.read()
        assert re.match(r'\[.*"ERROR", "before setup"', content) is None
        assert re.match(r'\[.*"ERROR",.*"after setup"', content)

    @mock.patch("uaclient.cli.config.UAConfig")
    def test_custom_logger_configuration(
        self,
        m_config,
        logging_sandbox,
        tmpdir,
        FakeConfig,
    ):
        log_file = tmpdir.join("file.log")
        cfg = FakeConfig({"log_file": log_file.strpath})
        m_config.return_value = cfg

        custom_logger = logging.getLogger("for-my-special-module")
        root_logger = logging.getLogger()
        n_root_handlers = len(root_logger.handlers)

        pro_log.setup_logging(logging.INFO, logging.INFO, logger=custom_logger)

        assert len(custom_logger.handlers) == 2
        assert len(root_logger.handlers) == n_root_handlers

    @mock.patch("uaclient.cli.config.UAConfig")
    def test_no_duplicate_ua_handlers(
        self,
        m_config,
        logging_sandbox,
        tmpdir,
        FakeConfig,
    ):
        log_file = tmpdir.join("file.log")
        cfg = FakeConfig({"log_file": log_file.strpath})
        m_config.return_value = cfg
        root_logger = logging.getLogger()

        pro_log.setup_logging(logging.INFO, logging.DEBUG)
        stream_handlers = [
            h
            for h in root_logger.handlers
            if h.level == logging.INFO and isinstance(h, logging.StreamHandler)
        ]
        file_handlers = [
            h
            for h in root_logger.handlers
            if h.level == logging.DEBUG
            and isinstance(h, logging.FileHandler)
            and h.stream.name == log_file
        ]
        assert len(root_logger.handlers) == 2
        assert len(stream_handlers) == 1
        assert len(file_handlers) == 1

        pro_log.setup_logging(logging.INFO, logging.DEBUG)
        stream_handlers = [
            h
            for h in root_logger.handlers
            if h.level == logging.INFO and isinstance(h, logging.StreamHandler)
        ]
        file_handlers = [
            h
            for h in root_logger.handlers
            if h.level == logging.DEBUG
            and isinstance(h, logging.FileHandler)
            and h.stream.name == log_file
        ]
        assert len(root_logger.handlers) == 2
        assert len(stream_handlers) == 1
        assert len(file_handlers) == 1

    @pytest.mark.parametrize("pre_existing", (True, False))
    @mock.patch("uaclient.cli.config")
    def test_file_log_is_world_readable(
        self,
        m_config,
        logging_sandbox,
        tmpdir,
        pre_existing,
    ):
        log_file = tmpdir.join("root-only.log")
        log_path = log_file.strpath
        expected_mode = 0o644
        if pre_existing:
            expected_mode = 0o640
            log_file.write("existing content\n")
            os.chmod(log_path, expected_mode)
            assert 0o644 != stat.S_IMODE(os.lstat(log_path).st_mode)

        pro_log.setup_logging(logging.INFO, logging.INFO, log_file=log_path)
        logging.info("after setup")

        assert expected_mode == stat.S_IMODE(os.lstat(log_path).st_mode)
        log_content = log_file.read()
        assert "after setup" in log_content
        if pre_existing:
            assert "existing content" in log_content
