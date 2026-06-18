"""Tests for newline/control-character injection prevention (F01)."""

import pytest

from uaclient import exceptions
from uaclient.apt import (
    _assert_no_apt_injection,
    _get_list_file_content,
    _get_sources_file_content,
)
from uaclient.data_types import (
    IncorrectListElementTypeError,
    IncorrectTypeError,
    StrictStringDataValue,
    data_list,
)


class TestStrictStringDataValue:
    """StrictStringDataValue rejects control characters."""

    @pytest.mark.parametrize(
        "val",
        (
            "hello",
            "jammy",
            "jammy-updates",
            "https://esm.ubuntu.com/infra/ubuntu",
            "my-package-name",
            "a" * 500,
        ),
    )
    def test_accepts_valid_strings(self, val):
        assert StrictStringDataValue.from_value(val) == val

    @pytest.mark.parametrize(
        "val",
        (
            "jammy\ndeb [trusted=yes] http://evil.example.com/repo jammy main",
            "https://esm.ubuntu.com\nhttps://evil.example.com",
            "value\rinjection",
            "value\x00injection",
            "\n",
            "\r",
            "\x00",
            "jammy main\ndeb http://attacker/ jammy main",
        ),
    )
    def test_rejects_control_characters(self, val):
        with pytest.raises(IncorrectTypeError) as exc_info:
            StrictStringDataValue.from_value(val)
        assert "control characters" in exc_info.value.msg

    @pytest.mark.parametrize("val", (1, True, [], {}))
    def test_rejects_non_strings(self, val):
        with pytest.raises(IncorrectTypeError):
            StrictStringDataValue.from_value(val)


class TestStrictStringDataValueInList:
    """data_list(StrictStringDataValue) rejects injection in list items."""

    def test_valid_list_passes(self):
        strict_list = data_list(StrictStringDataValue)
        result = strict_list.from_value(["jammy", "jammy-updates"])
        assert result == ["jammy", "jammy-updates"]

    def test_newline_in_list_item_raises(self):
        strict_list = data_list(StrictStringDataValue)
        with pytest.raises(IncorrectListElementTypeError):
            strict_list.from_value(
                ["jammy", "jammy\ndeb [trusted=yes] http://evil/ jammy main"]
            )


class TestAssertNoAptInjection:
    """Defense-in-depth validation at point of use in apt.py."""

    @pytest.mark.parametrize(
        "val",
        (
            "https://esm.ubuntu.com/infra/ubuntu",
            "jammy",
            "jammy-updates",
            "simple-package",
        ),
    )
    def test_accepts_clean_values(self, val):
        # Should not raise
        _assert_no_apt_injection(val, "test_field")

    @pytest.mark.parametrize(
        "val",
        (
            "jammy\ndeb [trusted=yes] http://evil/ jammy main",
            "https://example.com\nhttps://evil.com",
            "value\rcarriage-return",
            "null\x00byte",
        ),
    )
    def test_rejects_control_characters(self, val):
        with pytest.raises(exceptions.InvalidAPTDirectiveValueError):
            _assert_no_apt_injection(val, "test_field")


class TestGetListFileContentInjection:
    """_get_list_file_content refuses to produce malicious content."""

    def test_normal_suites_work(self):
        content = _get_list_file_content(
            suites=["jammy", "jammy-updates"],
            series="jammy",
            updates_enabled=True,
            repo_url="https://esm.ubuntu.com/infra/ubuntu",
        )
        assert "deb https://esm.ubuntu.com/infra/ubuntu jammy main" in content
        assert "jammy-updates" in content

    def test_newline_in_suite_raises(self):
        malicious_suite = (
            "jammy main\n"
            "deb [trusted=yes] http://attacker.example.com/repo jammy main"
        )
        with pytest.raises(exceptions.InvalidAPTDirectiveValueError):
            _get_list_file_content(
                suites=[malicious_suite],
                series="jammy",
                updates_enabled=True,
                repo_url="https://esm.ubuntu.com/infra/ubuntu",
            )

    def test_newline_in_repo_url_raises(self):
        with pytest.raises(exceptions.InvalidAPTDirectiveValueError):
            _get_list_file_content(
                suites=["jammy"],
                series="jammy",
                updates_enabled=True,
                repo_url="https://esm.ubuntu.com/infra/ubuntu\ndeb"
                " [trusted=yes] http://evil/ jammy main",
            )


class TestGetSourcesFileContentInjection:
    """_get_sources_file_content refuses to produce malicious content."""

    def test_newline_in_suite_raises(self):
        malicious_suite = (
            "jammy\n"
            "URIs: http://attacker.example.com/repo\n"
            "Signed-By: /dev/null"
        )
        with pytest.raises(exceptions.InvalidAPTDirectiveValueError):
            _get_sources_file_content(
                suites=[malicious_suite],
                series="jammy",
                updates_enabled=True,
                repo_url="https://esm.ubuntu.com/infra/ubuntu",
                keyring_file="ubuntu-pro-esm-infra.gpg",
            )

    def test_newline_in_repo_url_raises(self):
        with pytest.raises(exceptions.InvalidAPTDirectiveValueError):
            _get_sources_file_content(
                suites=["jammy"],
                series="jammy",
                updates_enabled=True,
                repo_url="https://esm.ubuntu.com\n"
                "URIs: http://evil.example.com",
                keyring_file="ubuntu-pro-esm-infra.gpg",
            )

    def test_newline_in_keyring_file_raises(self):
        with pytest.raises(exceptions.InvalidAPTDirectiveValueError):
            _get_sources_file_content(
                suites=["jammy"],
                series="jammy",
                updates_enabled=True,
                repo_url="https://esm.ubuntu.com/infra/ubuntu",
                keyring_file="key.gpg\nSigned-By: /dev/null",
            )
