import json
import re
from datetime import datetime
from typing import List

import click

DEFAULT_LOG_FILE = "/var/log/ubuntu-advantage.log"


class LogEntry:
    def __init__(self, log_data):
        self.timestamp = datetime.strptime(log_data[0], "%Y-%m-%dT%H:%M:%S.%f")
        self.level = log_data[1]
        self.module = log_data[2]
        self.called_function = log_data[3]
        self.line_number = log_data[4]
        self.message = log_data[5]
        self.metadata = log_data[6]
        if "exc_info" in self.metadata:
            self.exc_info = self.metadata["exc_info"]

    def format_traceback(self, traceback: str, color: bool = False) -> str:
        lines = traceback.split("\n")
        formatted_traceback = []

        for line in lines:
            line = line.strip()
            if line.startswith("File "):
                match = re.match(r'(.*")(.*)(".*)', line)
                if match and color:
                    formatted_line = f"{match.group(1)}{click.style(match.group(2), fg='cyan')}{match.group(3)}"  # noqa
                else:
                    formatted_line = line
            elif line.startswith("raise "):
                formatted_line = click.style(line, fg="red") if color else line
            else:
                formatted_line = line

            formatted_traceback.append(f"    {formatted_line}")

        return "\n".join(formatted_traceback)

    def format(self, color: bool = False) -> str:
        level_color = {
            "DEBUG": "cyan",
            "WARNING": "yellow",
            "ERROR": "red",
        }.get(self.level)

        formatted = click.style(
            f"[{self.timestamp}] {self.level}",
            fg=level_color if color else None,
        )
        formatted += f" - {self.module}.{self.called_function} (line {self.line_number}):\n"  # noqa
        formatted += f"    Message: {self.message}\n"

        if self.metadata and self.metadata != {}:
            formatted += "    Metadata:\n"
            for key, value in self.metadata.items():
                if key != "exc_info":
                    formatted += f"        {key}: {value}\n"

        if hasattr(self, "exc_info"):
            formatted += "    Exception Info:\n"
            formatted += self.format_traceback(self.exc_info, color)

        return formatted.strip()


class LogProcessor:
    def __init__(self, log_level, log_file=None, pattern=None):
        self.log_level = log_level
        self.log_file = log_file
        self.pattern = pattern

    def process(self) -> List[LogEntry]:
        if not self.log_file:
            self.log_file = DEFAULT_LOG_FILE
        with open(self.log_file, "r") as file:
            logs = [json.loads(line) for line in file.readlines()]
        return self.filter_logs([LogEntry(log_data) for log_data in logs])

    def filter_logs(self, logs: List[LogEntry]) -> List[LogEntry]:
        filtered = logs
        if self.log_level:
            filtered = [log for log in filtered if log.level == self.log_level]
        if self.pattern:
            regex = re.compile(self.pattern)
            filtered = [
                log
                for log in filtered
                if regex.search(log.message)
                or any(
                    regex.search(str(value)) for value in log.metadata.values()
                )
            ]
        return filtered


@click.command()
@click.argument(
    "log_level",
    type=click.Choice(["ERROR", "DEBUG", "WARNING"]),
    required=False,
)
@click.option(
    "-f",
    "--file",
    type=str,
    help="Log file to process",
)
@click.option(
    "-p",
    "--pattern",
    type=str,
    help="Regular expression pattern to filter logs",
)
def main(log_level, file, pattern):
    processor = LogProcessor(log_level, file, pattern)
    filtered_logs = processor.process()

    for log_entry in filtered_logs:
        print(log_entry.format(color=True))
        print("-" * 80)


if __name__ == "__main__":
    main()
