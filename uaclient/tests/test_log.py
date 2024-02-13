import json
import logging
from io import StringIO

import mock
import pytest

from uaclient import log as pro_log
from uaclient import util

LOG = logging.getLogger(util.replace_top_level_logger_name(__name__))
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
    @pytest.mark.parametrize("caplog_text", [logging.DEBUG], indirect=True)
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
        assert val[2] == util.replace_top_level_logger_name(__name__)
        assert val[5] == message
        if extra:
            assert val[6].get("key") == extra.get("key")
        else:
            assert 7 == len(val)


class TestLogHelpers:
    @pytest.mark.parametrize(
        [
            "we_are_currently_root",
            "expected",
        ],
        [
            (True, "cfg_log_file"),
            (False, "user_log_file"),
        ],
    )
    @mock.patch(
        "uaclient.log.get_user_log_file",
        return_value="user_log_file",
    )
    @mock.patch(
        "uaclient.config.UAConfig.log_file",
        new_callable=mock.PropertyMock,
        return_value="cfg_log_file",
    )
    @mock.patch("uaclient.util.we_are_currently_root")
    def test_get_user_or_root_log_file_path(
        self,
        m_we_are_currently_root,
        m_cfg_log_file,
        m_get_user_log_file,
        we_are_currently_root,
        expected,
    ):
        """
        Tests that the correct log_file path is retrieved
        when the user is root and non-root
        """
        m_we_are_currently_root.return_value = we_are_currently_root
        result = pro_log.get_user_or_root_log_file_path()
        # ensure mocks are used properly
        # assert m_we_are_currently_root.call_count == 2
        assert m_cfg_log_file.call_count + m_get_user_log_file.call_count == 1
        if we_are_currently_root:
            assert m_cfg_log_file.call_count == 1
        else:
            assert m_get_user_log_file.call_count == 1
        # ensure correct log_file path is returned
        assert expected == result
