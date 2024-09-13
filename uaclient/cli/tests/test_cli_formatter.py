import mock
import pytest

from uaclient.cli.formatter import ProOutputFormatterConfig as POFC
from uaclient.cli.formatter import len_no_color, wrap_text

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


class TestRealLength:
    @pytest.mark.parametrize(
        "input_string,expected_length",
        (
            ("", 0),
            ("input text", 10),
            ("\033[1mbold text\033[0m", 9),
            ("\033[91mred text\033[0m", 8),
            ("\033[1m\033[91mbold and red text\033[0m", 17),
            ("some \033[1mbold\033[0m and some \033[91mred\033[0m text", 27),
        ),
    )
    def test_length_ignores_color(self, input_string, expected_length):
        assert expected_length == len_no_color(input_string)


class TestWrapText:
    def test_single_line_wrapped(self):
        assert ["example"] == wrap_text("example", 20)

        long_string = (
            "Lorem ipsum dolor sit amet, consectetur adipiscing elit. "
            "Pellentesque diam nulla, efficitur a orci non, "
            "scelerisque lobortis felis."
        )
        assert [
            "Lorem ipsum dolor sit amet,",
            "consectetur adipiscing elit.",
            "Pellentesque diam nulla,",
            "efficitur a orci non,",
            "scelerisque lobortis felis.",
        ] == wrap_text(long_string, 30)

        colored_string = (
            "some \033[1mbold\033[0m and include "
            "the \033[91mred\033[0m text too"
        )
        assert len(colored_string) == 55
        assert [colored_string] == wrap_text(colored_string, 40)
        assert [
            "some \x1b[1mbold\x1b[0m and",
            "include the \x1b[91mred\x1b[0m text",
            "too",
        ] == wrap_text(colored_string, 20)
