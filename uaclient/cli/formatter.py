import abc
import os
import re
import sys
import textwrap
from enum import Enum
from typing import Any, Dict, List, Optional  # noqa: F401

from uaclient.config import UAConfig
from uaclient.messages import TxtColor

COLOR_FORMATTING_PATTERN = r"\033\[.*?m"
LINK_START_PATTERN = r"\033]8;;.+?\033\\+"
LINK_END = "\033]8;;\033\\"
UTF8_ALTERNATIVES = {
    "—": "-",
    "✘": "x",
    "✔": "*",
}  # type: Dict[str, str]


class ContentAlignment(Enum):
    LEFT = "l"
    RIGHT = "r"


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


def create_link(text: str, url: str) -> str:
    return "\033]8;;{url}\033\\{text}\033]8;;\033\\".format(url=url, text=text)


def real_len(text: str) -> int:
    # ignore colors if existing
    result = re.sub(COLOR_FORMATTING_PATTERN, "", text)
    # Ignore link control characters and metadata
    result = re.sub(LINK_START_PATTERN, "", result)
    result = result.replace(LINK_END, "")

    return len(result)


def _get_default_length():
    if sys.stdout.isatty():
        return os.get_terminal_size().columns
    # If you're not in a tty, we don't care about string length
    # If you have a thousand characters line, well, wow
    return 999


def process_formatter_config(text: str) -> str:
    output = text
    if not ProOutputFormatterConfig.use_color:
        output = re.sub(COLOR_FORMATTING_PATTERN, "", text)

    if not ProOutputFormatterConfig.use_utf8:
        for char, alternative in UTF8_ALTERNATIVES.items():
            output = output.replace(char, alternative)
        output = output.encode("ascii", "ignore").decode()

    if not sys.stdout.isatty():
        output = re.sub(LINK_START_PATTERN, "", output)
        output = output.replace(LINK_END, "")

    return output


# We can't rely on textwrap because of the real_len function
# Textwrap is using a magic regex instead
def wrap_text(text: str, max_width: int) -> List[str]:
    if real_len(text) <= max_width:
        return [text]

    words = text.split()
    wrapped_lines = []
    current_line = ""

    for word in words:
        if real_len(current_line) + real_len(word) >= max_width:
            wrapped_lines.append(current_line.strip())
            current_line = word
        else:
            current_line += " " + word

    if current_line:
        wrapped_lines.append(current_line.strip())

    return wrapped_lines


class ProOutputFormatter(abc.ABC):
    @abc.abstractmethod
    def to_string(self, line_length: Optional[int] = None) -> str:
        pass

    def __str__(self):
        return self.to_string()


class Table(ProOutputFormatter):
    SEPARATOR = " " * 2

    def __init__(
        self,
        headers: Optional[List[str]] = None,
        rows: Optional[List[List[str]]] = None,
        alignment: Optional[List[ContentAlignment]] = None,
    ):
        self.headers = headers if headers is not None else []
        self.rows = rows if rows is not None else []
        self.column_sizes = self._get_column_sizes()
        self.alignment = (
            alignment
            if alignment is not None
            else [ContentAlignment.LEFT] * len(self.column_sizes)
        )
        if len(self.alignment) != len(self.column_sizes):
            raise ValueError(
                "'alignment' list should have length {}".format(
                    len(self.column_sizes)
                )
            )
        self.last_column_size = self.column_sizes[-1]

    @staticmethod
    def ljust(string: str, total_length: int) -> str:
        str_length = real_len(string)
        if str_length >= total_length:
            return string
        return string + " " * (total_length - str_length)

    @staticmethod
    def rjust(string: str, total_length: int) -> str:
        str_length = real_len(string)
        if str_length >= total_length:
            return string
        return " " * (total_length - str_length) + string

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
                max(real_len(str(item[i])) for item in all_content)
            )

        return column_sizes

    def to_string(self, line_length: Optional[int] = None) -> str:
        if line_length is None:
            line_length = _get_default_length()

        rows = self.rows
        if self._get_line_length() > line_length:
            rows = self.wrap_last_column(line_length)
        output = ""
        if self.headers:
            output += (
                TxtColor.BOLD
                + self._fill_row(self.headers)
                + TxtColor.ENDC
                + "\n"
            )
        for row in rows:
            output += self._fill_row(row)
            output += "\n"

        return process_formatter_config(output)

    def _get_line_length(self) -> int:
        return sum(self.column_sizes) + (len(self.column_sizes) - 1) * len(
            self.SEPARATOR
        )

    def wrap_last_column(self, max_length: int) -> List[List[str]]:
        self.last_column_size = max_length - (
            sum(self.column_sizes[:-1])
            + (len(self.column_sizes) - 1) * len(self.SEPARATOR)
        )
        new_rows = []
        for row in self.rows:
            if len(row[-1]) <= self.last_column_size:
                new_rows.append(row)
            else:
                wrapped_last_column = wrap_text(row[-1], self.last_column_size)
                new_rows.append(row[:-1] + [wrapped_last_column[0]])
                for extra_line in wrapped_last_column[1:]:
                    new_row = [" "] * (len(self.column_sizes) - 1) + [
                        extra_line
                    ]
                    new_rows.append(new_row)
        return new_rows

    def _fill_row(self, row: List[str]) -> str:
        output = ""
        for i in range(len(row) - 1):
            if self.alignment[i] == ContentAlignment.LEFT:
                output += (
                    self.ljust(row[i], self.column_sizes[i]) + self.SEPARATOR
                )
            elif self.alignment[i] == ContentAlignment.RIGHT:
                output += (
                    self.rjust(row[i], self.column_sizes[i]) + self.SEPARATOR
                )
        if self.alignment[-1] == ContentAlignment.LEFT:
            output += row[-1]
        elif self.alignment[-1] == ContentAlignment.RIGHT:
            output += self.rjust(row[-1], self.last_column_size)
        return output


class Block(ProOutputFormatter):
    INDENT_SIZE = 4
    INDENT_CHAR = " "

    def __init__(
        self,
        title: Optional[str] = None,
        content: Optional[List[Any]] = None,
    ):
        self.title = title
        self.content = content if content is not None else []

    def to_string(self, line_length: Optional[int] = None) -> str:
        if line_length is None:
            line_length = _get_default_length()

        line_length -= self.INDENT_SIZE

        output = ""

        if self.title:
            output += (
                TxtColor.BOLD
                + TxtColor.DISABLEGREY
                + self.title
                + TxtColor.ENDC
                + "\n"
            )

        for item in self.content:
            if isinstance(item, ProOutputFormatter):
                item_str = item.to_string(line_length=line_length)
            else:
                item_str = "\n".join(wrap_text(str(item), line_length)) + "\n"

            output += textwrap.indent(
                item_str, self.INDENT_CHAR * self.INDENT_SIZE
            )

        return process_formatter_config(output)


class SuggestionBlock(Block):
    def to_string(self, line_length: Optional[int] = None) -> str:
        if ProOutputFormatterConfig.show_suggestions:
            return super().to_string(line_length)
        return ""
