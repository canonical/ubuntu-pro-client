import os
import re
import sys
from typing import List, Optional

from uaclient.config import UAConfig
from uaclient.messages import TxtColor

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


class Table:
    SEPARATOR = " " * 2

    def __init__(
        self,
        headers: Optional[List[str]] = None,
        rows: Optional[List[List[str]]] = None,
        max_length: Optional[int] = None,
    ):
        self.headers = headers if headers is not None else []
        self.rows = rows if rows is not None else []
        self.column_sizes = self._get_column_sizes()
        if sys.stdout.isatty():
            self.max_length = (
                os.get_terminal_size().columns
                if max_length is None
                else max_length
            )
        else:
            # If you're not in a tty, we don't care about wrapping
            # If you have a thousand characters line on the table, well, wow
            self.max_length = 999

    @staticmethod
    def ljust(string: str, total_length: int) -> str:
        str_length = len_no_color(string)
        if str_length >= total_length:
            return string
        return string + " " * (total_length - str_length)

    def _get_column_sizes(self) -> List[int]:
        if not self.headers and not self.rows:
            raise ValueError(
                "Empty table not supported. Please provide headers or rows."
            )

        if self.rows and any(len(item) == 0 for item in self.rows):
            raise ValueError(
                "Empty row not supported. Please provide content for each row."
            )

        all_content = []
        if self.headers:
            all_content.append(self.headers)
        if self.rows:
            all_content.extend(self.rows)

        expected_length = len(all_content[0])
        if not all(len(item) == expected_length for item in all_content):
            raise ValueError(
                "Mixed lengths in table content. "
                "Please provide headers / rows of the same length."
            )

        column_sizes = []
        for i in range(len(all_content[0])):
            column_sizes.append(
                max(len_no_color(str(item[i])) for item in all_content)
            )

        return column_sizes

    def __str__(self) -> str:
        if self._get_line_length() > self.max_length:
            self.rows = self.wrap_last_column()
        output = ""
        output += TxtColor.BOLD + self._fill_row(self.headers) + TxtColor.ENDC
        for row in self.rows:
            output += "\n"
            output += self._fill_row(row)
        return output

    def _get_line_length(self) -> int:
        return sum(self.column_sizes) + (len(self.column_sizes) - 1) * len(
            self.SEPARATOR
        )

    def wrap_last_column(self) -> List[List[str]]:
        last_column_size = self.max_length - (
            sum(self.column_sizes[:-1])
            + (len(self.column_sizes) - 1) * len(self.SEPARATOR)
        )
        new_rows = []
        for row in self.rows:
            if len(row[-1]) <= last_column_size:
                new_rows.append(row)
            else:
                wrapped_last_column = wrap_text(row[-1], last_column_size)
                row[-1] = wrapped_last_column[0]
                new_rows.append(row)
                for extra_line in wrapped_last_column[1:]:
                    new_row = [" "] * (len(self.column_sizes) - 1) + [
                        extra_line
                    ]
                    new_rows.append(new_row)
        return new_rows

    def _fill_row(self, row: List[str]) -> str:
        output = ""
        for i in range(len(row) - 1):
            output += self.ljust(row[i], self.column_sizes[i]) + self.SEPARATOR
        output += row[-1]
        return output