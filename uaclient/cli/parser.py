import argparse
from collections import OrderedDict
from typing import List, NamedTuple  # noqa: F401

from uaclient import messages

HelpEntry = NamedTuple(
    "HelpEntry", [("position", int), ("name", str), ("help_string", str)]
)


class ProArgumentParser(argparse.ArgumentParser):
    help_entries = OrderedDict(
        [
            (messages.CLI_HELP_HEADER_QUICK_START, []),
            (messages.CLI_HELP_HEADER_SECURITY, []),
            (messages.CLI_HELP_HEADER_TROUBLESHOOT, []),
            (messages.CLI_HELP_HEADER_OTHER, []),
            (messages.CLI_FLAGS, []),
        ]
    )  # type: OrderedDict[str, List[HelpEntry]]

    @classmethod
    def add_help_entry(
        cls, category: str, name: str, help_string: str, position: int = 0
    ):
        cls.help_entries[category].append(
            HelpEntry(position=position, name=name, help_string=help_string)
        )

    def __init__(self, *args, use_main_help: bool = True, **kwargs):
        super().__init__(*args, **kwargs)
        self.use_main_help = use_main_help

    def print_help_for_command(self, command: str):
        args_list = command.split()
        args_list.append("--help")
        try:
            self.parse_args(args_list)
        # We want help for any specific command,
        # but without exiting right after
        except SystemExit:
            pass

    def format_help(self):
        if self.use_main_help:
            return super().format_help()
        help_output = self.format_usage()

        for category, items in self.help_entries.items():
            help_output += "\n"
            help_output += "{}:".format(category)
            help_output += "\n"
            for item in sorted(items, key=lambda item: item.position):
                help_output += "\n"
                help_output += "  {:<17}{}".format(item.name, item.help_string)
            help_output += "\n"
        if self.epilog:
            help_output += "\n"
            help_output += self.epilog
            help_output += "\n"

        return help_output
