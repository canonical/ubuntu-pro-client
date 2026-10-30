import io
import json
import logging

import mock
import pytest

from features.util import (
    RedactingFormatter,
    process_template_vars,
    redact,
    redact_log_handlers,
    redaction_markers,
)

TOKEN = "C1secrettoken0123456789abcdef"
STAGING_TOKEN = "C1stagingtoken0123456789abcde"
TOKEN_MARKER = "<REDACTED:contract_token>"


class TestRedactionMarkers:
    @pytest.mark.parametrize(
        "secrets,expected",
        (
            ({"contract_token": TOKEN}, [(TOKEN, TOKEN_MARKER)]),
            # Unset options have nothing to redact.
            ({"contract_token": None, "contract_token_staging": ""}, []),
            # One value set under two options names both.
            (
                {"contract_token_staging": TOKEN, "contract_token": TOKEN},
                [
                    (
                        TOKEN,
                        "<REDACTED:contract_token,contract_token_staging>",
                    )
                ],
            ),
            # A value that contains another comes first.
            (
                {"short": "abc", "long": "abcdef"},
                [
                    ("abcdef", "<REDACTED:long>"),
                    ("abc", "<REDACTED:short>"),
                ],
            ),
        ),
    )
    def test_redaction_markers(self, secrets, expected):
        assert expected == redaction_markers(secrets)


class TestRedact:
    @pytest.mark.parametrize(
        "text,secrets,expected",
        (
            ("no secrets here", {"contract_token": TOKEN}, "no secrets here"),
            (
                "pro attach {} && pro attach {}".format(TOKEN, TOKEN),
                {"contract_token": TOKEN},
                "pro attach {} && pro attach {}".format(
                    TOKEN_MARKER, TOKEN_MARKER
                ),
            ),
            (
                "key=abcdef",
                {"short": "abc", "long": "abcdef"},
                "key=<REDACTED:long>",
            ),
            ("unchanged", {}, "unchanged"),
        ),
    )
    def test_redact(self, text, secrets, expected):
        assert expected == redact(text, redaction_markers(secrets))


class JsonFormatter(logging.Formatter):
    """Renders the exception from exc_info itself, ignoring exc_text."""

    def format(self, record):
        entry = {"message": record.getMessage()}
        if record.exc_info:
            entry["exc_info"] = self.formatException(record.exc_info)
        return json.dumps(entry)


class RecordingHandler(logging.Handler):
    """A downstream handler that keeps the records it receives."""

    def __init__(self):
        super().__init__()
        self.records = []

    def emit(self, record):
        self.records.append(record)


@pytest.fixture
def parent_logger():
    """A logger with one handler, standing in for behave's root logger."""
    logger = logging.getLogger("redaction_test")
    logger.propagate = False
    logger.setLevel(logging.INFO)
    stream = io.StringIO()
    handler = logging.StreamHandler(stream)
    handler.setFormatter(logging.Formatter("%(name)s:%(message)s"))
    logger.handlers = [handler]
    yield logger, stream
    logger.handlers = []


class TestRedactLogHandlers:
    def test_redacts_records_from_child_loggers(self, parent_logger):
        logger, stream = parent_logger
        redact_log_handlers(
            {
                "contract_token": TOKEN,
                "contract_token_legacy": None,
                "contract_token_staging": "",
            },
            logger=logger,
        )

        # pycloudlib's loggers have no handlers and propagate to root.
        logging.getLogger("redaction_test.pycloudlib.instance").info(
            "executing: %s", "sudo pro attach {}".format(TOKEN)
        )
        logger.info("--- Retrying on exit 1: pro attach {}".format(TOKEN))

        assert [
            "redaction_test.pycloudlib.instance:executing: sudo pro attach "
            + TOKEN_MARKER,
            "redaction_test:--- Retrying on exit 1: pro attach "
            + TOKEN_MARKER,
        ] == stream.getvalue().splitlines()

    @pytest.mark.parametrize(
        "formatter", (logging.Formatter("%(message)s"), JsonFormatter())
    )
    def test_redacts_exceptions(self, parent_logger, formatter):
        logger, stream = parent_logger
        logger.handlers[0].setFormatter(formatter)
        redact_log_handlers({"contract_token": TOKEN}, logger=logger)

        try:
            raise RuntimeError("attach failed for {}".format(TOKEN))
        except RuntimeError:
            logger.exception("command failed")

        assert "attach failed for {}".format(TOKEN_MARKER) in stream.getvalue()
        assert TOKEN not in stream.getvalue()

    def test_downstream_handlers_get_the_full_record(self, parent_logger):
        logger, stream = parent_logger
        recorder = RecordingHandler()
        logger.addHandler(recorder)
        redact_log_handlers({"contract_token": TOKEN}, logger=logger)

        try:
            raise RuntimeError(TOKEN)
        except RuntimeError:
            logger.exception("attach %s", TOKEN)

        [record] = recorder.records
        assert (TOKEN,) == record.args
        assert TOKEN == str(record.exc_info[1])

    def test_wraps_each_handler_once(self, parent_logger):
        logger, stream = parent_logger
        secrets = {"contract_token": TOKEN}

        redact_log_handlers(secrets, logger=logger)
        wrapped = logger.handlers[0].formatter
        redact_log_handlers(secrets, logger=logger)

        assert isinstance(wrapped, RedactingFormatter)
        assert wrapped is logger.handlers[0].formatter
        assert not isinstance(wrapped.inner, RedactingFormatter)

    def test_no_secrets_leaves_handlers_alone(self, parent_logger):
        logger, stream = parent_logger
        formatter = logger.handlers[0].formatter

        redact_log_handlers(
            {"contract_token": None, "landscape_key": ""}, logger=logger
        )

        assert formatter is logger.handlers[0].formatter


class TestProcessTemplateVars:
    @pytest.mark.parametrize(
        "template,shown,expected",
        (
            ("$behave_var{contract_token}", False, TOKEN),
            ("$behave_var{contract_token_staging}", False, STAGING_TOKEN),
            ("$behave_var{config contract_token}", False, TOKEN),
            # Text that behave shows keeps its secrets as placeholders.
            (
                "$behave_var{contract_token}",
                True,
                "$behave_var{contract_token}",
            ),
            (
                "$behave_var{contract_token_staging}",
                True,
                "$behave_var{contract_token_staging}",
            ),
            (
                "$behave_var{config contract_token}",
                True,
                "$behave_var{config contract_token}",
            ),
        ),
    )
    def test_secrets(self, template, shown, expected):
        context = mock.MagicMock()
        context.pro_config.contract_token = TOKEN
        context.pro_config.contract_token_staging = STAGING_TOKEN
        context.pro_config.redact_options = [
            "contract_token",
            "contract_token_staging",
        ]

        assert expected == process_template_vars(
            context, template, logger_fn=mock.Mock(), shown=shown
        )
