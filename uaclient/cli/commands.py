import argparse
from typing import Callable, Iterable, Optional, Union

from uaclient import messages
from uaclient.cli.parser import HelpCategory


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

    def register(
        self, target: Union[argparse.ArgumentParser, argparse._ArgumentGroup]
    ):
        target.add_argument(
            *self.names, help=self.help, **self.additional_args
        )


class ProArgumentMutuallyExclusiveGroup:
    def __init__(
        self,
        required: bool = False,
        arguments: Iterable[ProArgument] = (),
    ):
        self.required = required
        self.arguments = arguments


class ProArgumentGroup:
    def __init__(
        self,
        title: Optional[str] = None,
        description: Optional[str] = None,
        arguments: Iterable[ProArgument] = (),
        mutually_exclusive_groups: Iterable[
            ProArgumentMutuallyExclusiveGroup
        ] = (),
    ):
        self.title = title
        self.description = description
        self.arguments = arguments
        self.mutually_exclusive_groups = mutually_exclusive_groups

    def register(self, parser: argparse.ArgumentParser):
        target = (
            parser
        )  # type: Union[argparse.ArgumentParser, argparse._ArgumentGroup]
        if self.title:
            target = parser.add_argument_group(self.title, self.description)

        for argument in self.arguments:
            argument.register(target)

        for group in self.mutually_exclusive_groups:
            new_group = target.add_mutually_exclusive_group(
                required=group.required
            )
            for argument in group.arguments:
                argument.register(new_group)


class ProCommand:
    def __init__(
        self,
        name: str,
        help: str,
        description: str,
        action: Callable = lambda *args, **kwargs: None,
        preserve_description: bool = False,
        argument_groups: Iterable[ProArgumentGroup] = (),
        subcommands: Iterable["ProCommand"] = (),
        help_category: Optional[HelpCategory] = None,
        help_position: int = 0,
    ):
        self.name = name
        self.help = help
        self.description = description
        self.action = action
        self.preserve_description = preserve_description
        self.argument_groups = argument_groups
        self.subcommands = subcommands
        self.help_category = help_category
        self.help_position = help_position

    def register(self, subparsers: argparse._SubParsersAction):
        self.parser = subparsers.add_parser(
            self.name,
            help=self.help,
            description=self.description,
        )
        if self.preserve_description:
            self.parser.formatter_class = argparse.RawDescriptionHelpFormatter

        if self.help_category:
            self.parser.add_help_entry(
                category=self.help_category,
                name=self.name,
                help_string=self.help,
                position=self.help_position,
            )

        for argument_group in self.argument_groups:
            argument_group.register(self.parser)

        self.parser.set_defaults(action=self.action)

        if self.subcommands:
            subparsers = self.parser.add_subparsers(
                title=messages.CLI_AVAILABLE_COMMANDS,
                dest="command",
            )
            for command in self.subcommands:
                command.register(subparsers)
