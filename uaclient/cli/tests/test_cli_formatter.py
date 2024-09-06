import mock
import pytest

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
