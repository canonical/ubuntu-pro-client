import mock
import pytest

from uaclient.cli.formatter import ProColorString
from uaclient.cli.formatter import ProOutputFormatterConfig as POFC

M_PATH = "uaclient.cli.formatter."


class TestProFormatterConfig:
    @pytest.mark.parametrize(
        "system_encoding,expected_use_utf8",
        ((None, False), ("iso-8859-13", False), ("utf-8", True)),
    )
    def test_use_utf8(self, system_encoding, expected_use_utf8, FakeConfig):
        cfg = FakeConfig()

        with mock.patch(M_PATH + "sys.stdout") as m_stdout:
            m_stdout.encoding = system_encoding
            POFC.init(cfg)

        assert POFC.use_utf8 is expected_use_utf8

    @pytest.mark.parametrize("config_value", (True, False))
    @pytest.mark.parametrize("is_tty", (True, False))
    @pytest.mark.parametrize("env_no_color", ("True", None))
    @mock.patch(M_PATH + "sys.stdout.isatty")
    @mock.patch(M_PATH + "os.getenv")
    def test_color_config(
        self,
        m_getenv,
        m_is_tty,
        config_value,
        is_tty,
        env_no_color,
        FakeConfig,
    ):
        cfg = FakeConfig()
        cfg.user_config.cli_color = config_value

        m_is_tty.return_value = is_tty

        m_getenv.return_value = env_no_color

        POFC.init(cfg)

        expected_result = True
        if any((config_value is False, not is_tty, env_no_color)):
            expected_result = False

        assert POFC.use_color is expected_result

        POFC.disable_color()
        assert POFC.use_color is False

    @pytest.mark.parametrize("config_value", (True, False))
    def test_suggestions_config(self, config_value, FakeConfig):
        cfg = FakeConfig()
        cfg.user_config.cli_suggestions = config_value

        POFC.init(cfg)

        assert POFC.show_suggestions is config_value

        POFC.disable_suggestions()
        assert POFC.show_suggestions is False


class TestProColorString:
    def test_color_string_is_a_string(self):
        test = ProColorString("test str")
        assert isinstance(test, ProColorString)
        assert isinstance(test, str)
        "test str" == test

    @pytest.mark.parametrize(
        "input_string,target_string",
        (
            (None, "None"),
            ("", ""),
            ("input text", "input text"),
            ("\033[1mbold text\033[0m", "bold text"),
            ("\033[91mred text\033[0m", "red text"),
            (
                "\033[1m\033[91mbold and red text\033[0m",
                "bold and red text",
            ),
            (
                "some \033[1mbold\033[0m and some \033[91mred\033[0m text",
                "some bold and some red text",
            ),
        ),
    )
    def test_decolorize(self, input_string, target_string):
        test_string = ProColorString(input_string)
        assert target_string == test_string.decolorize()

    @pytest.mark.parametrize(
        "input_string,expected_length",
        (
            (None, 4),
            ("", 0),
            ("input text", 10),
            ("\033[1mbold text\033[0m", 9),
            ("\033[91mred text\033[0m", 8),
            ("\033[1m\033[91mbold and red text\033[0m", 17),
            ("some \033[1mbold\033[0m and some \033[91mred\033[0m text", 27),
        ),
    )
    def test_length_ignores_color(self, input_string, expected_length):
        assert expected_length == len(ProColorString(input_string))

    @pytest.mark.parametrize(
        "first_string,second_string,expected_result",
        (
            (
                "string before ",
                ProColorString("\033[1mbold text\033[0m"),
                "string before \033[1mbold text\033[0m",
            ),
            (
                ProColorString("\033[1mbold text\033[0m"),
                " string after",
                "\033[1mbold text\033[0m string after",
            ),
            (
                ProColorString("\033[1mbold text\033[0m"),
                ProColorString(" \033[1mbold text\033[0m"),
                "\033[1mbold text\033[0m \033[1mbold text\033[0m",
            ),
        ),
    )
    def test_concatenates_to_color_string(
        self, first_string, second_string, expected_result
    ):
        target_string = first_string + second_string

        assert target_string == expected_result
        assert isinstance(target_string, ProColorString)

    def test_split_produces_color_strings(self):
        test_string = ProColorString(
            "some \033[1mbold text\033[0m and some \033[91mred text\033[0m."
        )
        splitted = test_string.split()

        assert [
            "some",
            "\033[1mbold",
            "text\033[0m",
            "and",
            "some",
            "\033[91mred",
            "text\033[0m.",
        ] == splitted
        for chunk in splitted:
            assert isinstance(chunk, ProColorString)
