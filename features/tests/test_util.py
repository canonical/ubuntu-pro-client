import io
import logging

import mock
import pytest

from features.util import (
    RedactingRecordFactory,
    install_log_redaction,
    process_template_vars,
    redact,
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


def make_record(factory, msg, args=(), exc_info=None, sinfo=None):
    """Make a record the way Logger.makeRecord calls the factory."""
    return factory(
        "pycloudlib.instance",
        logging.INFO,
        __file__,
        1,
        msg,
        args,
        exc_info,
        sinfo=sinfo,
    )


def redacting_factory(make=logging.LogRecord):
    return RedactingRecordFactory(
        make, redaction_markers({"contract_token": TOKEN})
    )


def record_fields(record):
    return {
        "msg": record.msg,
        "args": record.args,
        "exc_info": record.exc_info,
        "stack_info": record.stack_info,
    }


class TestRedactingRecordFactory:
    def test_merges_args_into_redacted_message(self):
        factory = redacting_factory()

        record = make_record(
            factory, "executing: %s", ("sudo pro attach {}".format(TOKEN),)
        )

        assert {
            "msg": "executing: sudo pro attach " + TOKEN_MARKER,
            "args": (),
            "exc_info": None,
            "stack_info": None,
        } == record_fields(record)

    def test_args_that_do_not_match_the_format_are_appended(self):
        factory = redacting_factory()

        record = make_record(factory, "attach %s %s", (TOKEN,))

        assert "attach %s %s ('{}',)".format(TOKEN_MARKER) == record.msg

    def test_replaces_exc_info_with_redacted_exc_text(self):
        factory = redacting_factory()
        error = RuntimeError("attach failed for {}".format(TOKEN))

        record = make_record(
            factory,
            "command failed",
            exc_info=(RuntimeError, error, error.__traceback__),
        )

        assert None is record.exc_info
        assert (
            "RuntimeError: attach failed for {}".format(TOKEN_MARKER)
            == record.exc_text
        )

    def test_redacts_stack_info(self):
        factory = redacting_factory()

        record = make_record(
            factory, "attaching", sinfo="Stack:\n  attach({})".format(TOKEN)
        )

        assert "Stack:\n  attach({})".format(TOKEN_MARKER) == record.stack_info

    def test_uses_the_previous_factory(self):
        def tagging_factory(*args, **kwargs):
            record = logging.LogRecord(*args, **kwargs)
            record.made_by = "tagging_factory"
            return record

        factory = redacting_factory(make=tagging_factory)

        record = make_record(factory, "attaching")

        assert "tagging_factory" == record.made_by


@pytest.fixture
def record_factory():
    """Restore the global record factory that a test replaces."""
    original = logging.getLogRecordFactory()
    yield original
    logging.setLogRecordFactory(original)


@pytest.fixture
def isolated_logger():
    """A logger that doesn't propagate, with its handlers removed after."""
    logger = logging.getLogger("redaction_test")
    logger.propagate = False
    logger.setLevel(logging.INFO)
    yield logger
    logger.handlers = []


class TestInstallLogRedaction:
    def test_redacts_output_of_handlers_added_later(
        self, record_factory, isolated_logger
    ):
        install_log_redaction({"contract_token": TOKEN})
        stream = io.StringIO()
        handler = logging.StreamHandler(stream)
        handler.setFormatter(logging.Formatter("%(name)s:%(message)s"))
        isolated_logger.addHandler(handler)

        logging.getLogger("redaction_test.pycloudlib.instance").info(
            "executing: %s", "sudo pro attach {}".format(TOKEN)
        )

        assert [
            "redaction_test.pycloudlib.instance:executing: sudo pro attach "
            + TOKEN_MARKER
        ] == stream.getvalue().splitlines()

    def test_no_secrets_keeps_the_factory(self, record_factory):
        install_log_redaction(
            {"contract_token": None, "landscape_registration_key": ""}
        )

        assert record_factory is logging.getLogRecordFactory()


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
