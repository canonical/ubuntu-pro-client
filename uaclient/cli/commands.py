import argparse
from typing import Callable, List, Optional

from uaclient.cli.constants import NAME, USAGE_TMPL


class ProArgument:
    def __init__(
        self,
        long_name: str,
        help: str,
        short_name: Optional[str] = None,
        **kwargs
    ):
        self.names = (
            (long_name,) if short_name is None else (short_name, long_name)
        )
        self.help = help
        self.additional_args = kwargs

    def register(self, parser: argparse.ArgumentParser):
        parser.add_argument(
            *self.names, help=self.help, **self.additional_args
        )


class ProCommand:
    def __init__(
        self,
        name: str,
        help: str,
        description: str,
        usage: Optional[str] = None,
        action: Callable = lambda *args, **kwargs: None,
        arguments: List[ProArgument] = [],
    ):
        self.name = name
        self.help = help
        self.description = description
        self.usage = usage or USAGE_TMPL.format(name=NAME, command=name)
        self.action = action
        self.arguments = arguments

    def register(self, subparsers: argparse._SubParsersAction):
        self.parser = subparsers.add_parser(
            self.name,
            help=self.help,
            description=self.description,
            usage=self.usage,
        )
        for argument in self.arguments:
            argument.register(self.parser)
        self.parser.set_defaults(action=self.action)
