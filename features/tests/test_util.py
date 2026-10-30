import logging

import mock
import pytest

from features.util import (
    install_log_redaction,
    process_template_vars,
    redact,
    redaction_markers,
)

TOKEN = "C1secrettoken0123456789abcdef"
STAGING_TOKEN = "C1stagingtoken0123456789abcde"
TOKEN_MARKER = "<REDACTED:contract_token>"


@pytest.fixture
def restore_record_factory():
    factory = logging.getLogRecordFactory()
    yield
    logging.setLogRecordFactory(factory)


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


@pytest.mark.usefixtures("restore_record_factory")
class TestInstallLogRedaction:
    def test_redacts_messages_from_any_logger(self, caplog):
        install_log_redaction(
            {
                "contract_token": TOKEN,
                "contract_token_legacy": None,
                "contract_token_staging": "",
            }
        )
        caplog.set_level(logging.INFO)

        logging.getLogger("pycloudlib.instance").info(
            "executing: %s", "sudo pro attach {}".format(TOKEN)
        )
        logging.info("--- Retrying on exit 1: pro attach {}".format(TOKEN))

        assert [
            "executing: sudo pro attach {}".format(TOKEN_MARKER),
            "--- Retrying on exit 1: pro attach {}".format(TOKEN_MARKER),
        ] == [record.getMessage() for record in caplog.records]
        assert TOKEN not in caplog.text

    def test_redacts_exception_text(self, caplog):
        install_log_redaction({"contract_token": TOKEN})

        try:
            raise RuntimeError("attach failed for {}".format(TOKEN))
        except RuntimeError:
            logging.exception("command failed")

        assert "attach failed for {}".format(TOKEN_MARKER) in caplog.text
        assert TOKEN not in caplog.text

    def test_bad_format_args_do_not_raise(self, caplog):
        install_log_redaction({"contract_token": TOKEN})

        logging.warning("%s and %s", TOKEN)

        assert TOKEN not in caplog.text

    def test_no_secrets_leaves_the_factory_alone(self):
        factory = logging.getLogRecordFactory()

        install_log_redaction({"contract_token": None, "landscape_key": ""})

        assert factory is logging.getLogRecordFactory()


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
