import os
import re
import sys
from enum import Enum

from uaclient.config import UAConfig


class TxtColor(Enum):
    BLUE = "\033[94m"
    BOLD = "\033[1m"
    GREEN = "\033[92m"
    GREY = "\033[37m"
    ORANGE = "\033[38;5;208m"
    RED = "\033[91m"
    YELLOW = "\033[93m"
    ENDC = "\033[0m"


# Class attributes and methods so we don't need singletons or globals for this
class ProOutputFormatterConfig:
    use_utf8 = True
    use_color = True
    show_suggestions = True

    # Initializing the class after the import is useful for unit testing
    @classmethod
    def init(cls, cfg: UAConfig):
        cls.use_utf8 = (
            sys.stdout.encoding is not None
            and "UTF-8" in sys.stdout.encoding.upper()
        )

        cls.use_color = (
            sys.stdout.isatty()
            and os.getenv("NO_COLOR") is None
            and cfg.cli_color
        )

        cls.show_suggestions = cfg.cli_suggestions

    @classmethod
    def disable_color(cls) -> None:
        cls.use_color = False

    @classmethod
    def disable_suggestions(cls) -> None:
        cls.show_suggestions = False


ProOutputFormatterConfig.init(cfg=UAConfig())


class ProColorString(str):
    _formatting_pattern = r"\033\[.*?m"

    def __add__(self, other):
        return self.__class__(str(self) + other)

    def __radd__(self, other):
        return self.__class__(other + str(self))

    def __len__(self):
        return len(self.decolorize())

    def decolorize(self):
        return re.sub(self._formatting_pattern, "", self)

    def split(self, sep=None, maxsplit=-1):
        splitted = super().split(sep=sep, maxsplit=maxsplit)
        return [self.__class__(s) for s in splitted]


def colorize(input_string: str, color: TxtColor) -> str:
    if not ProOutputFormatterConfig.use_color:
        return input_string

    return_string = ProColorString(color.value + input_string)
    if not return_string.endswith(TxtColor.ENDC.value):
        return_string += TxtColor.ENDC.value

    return return_string
