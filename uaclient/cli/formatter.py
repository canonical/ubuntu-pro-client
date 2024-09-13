import os
import re
import sys
from typing import List

from uaclient.config import UAConfig

COLOR_FORMATTING_PATTERN = r"\033\[.*?m"


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


def len_no_color(text: str) -> int:
    return len(re.sub(COLOR_FORMATTING_PATTERN, "", text))


# We can't rely on textwrap because of the len_no_color function
# Textwrap is using a magic regex instead
def wrap_text(text: str, max_width: int) -> List[str]:
    if len_no_color(text) < max_width:
        return [text]

    words = text.split()
    wrapped_lines = []
    current_line = ""

    for word in words:
        if len_no_color(current_line) + len_no_color(word) >= max_width:
            wrapped_lines.append(current_line.strip())
            current_line = word
        else:
            current_line += " " + word

    if current_line:
        wrapped_lines.append(current_line.strip())

    return wrapped_lines
