#!/usr/bin/python3
"""
Generate documentation for an ubuntu-pro-client cli commands.
"""

import sys

sys.path.insert(0, ".")

from uaclient.cli import COMMANDS, get_parser
from uaclient.cli.commands import ProCommand

VALID_TARGETS = ["manpage", "rst"]

GENERATED_DOC_HEADER = """\
..
   THIS DOCUMENTATION WAS AUTOMATICALLY GENERATED
   Do not edit this document directly. Instead, edit the commands in the cli
   source code, which can be found on the main branch of the git repo at
   https://github.com/canonical/ubuntu-pro-client. The cli source code is
   nested in the uaclient/cli folder. Description for the commands is found
   in the uaclient/messages folder.

Available commands
==================

The currently available commands are:

{commands_list}

"""
COMMAND_LINK_TEMPLATE = "- `{command_entry}`_\n"

RST_TEMPLATE = """\
{command}
{section_mark}

**Usage:**

``{usage_line}``

**Description:**

{description}

"""

MANPAGE_TEMPLATE = """\
.TP
.BR "{indent}{name}" " {usage_options}"
{description}

"""


def _build_rst_entry(command: ProCommand, section_mark: str = "="):
    return RST_TEMPLATE.format(
        command=command.parser.prog,
        section_mark=section_mark * len(command.parser.prog),
        usage_line=" ".join(
            command.parser.format_usage()[len("usage: ") :].split()
        ),
        description=command.description,
    )


def _build_manpage_entry(command: ProCommand, indent: str = "") -> str:
    # the usage line looks like
    # usage: <prog> <options>
    # we want only the <options>
    options_line = command.parser.format_usage().split(command.parser.prog)[1]
    # Remove extra spaces and eventual newlines
    usage_options = " ".join(options_line.split())

    return MANPAGE_TEMPLATE.format(
        indent=indent,
        name=command.name,
        usage_options=usage_options,
        description=command.description,
    )


def _print_rst_section():
    command_list = ""
    for command in COMMANDS:
        command_list += COMMAND_LINK_TEMPLATE.format(
            command_entry=command.parser.prog
        )

    content = GENERATED_DOC_HEADER.format(commands_list=command_list)
    for command in COMMANDS:
        content += _build_rst_entry(command)
        for subcommand in command.subcommands:
            content += _build_rst_entry(subcommand, section_mark="-")

    print(content)


def _generate_manpage_section():
    result = ""
    for command in COMMANDS:
        result += _build_manpage_entry(command)
        for subcommand in command.subcommands:
            result += _build_manpage_entry(subcommand, indent=" " * 4)

    with open("./ubuntu-advantage.1.template", "r") as f:
        template = f.read()
    content = template.replace("<<commands_description>>", result)
    with open("./ubuntu-advantage.1", "w") as f:
        f.write(content)


if __name__ == "__main__":
    # get a parser so we register all the commands
    _parser = get_parser()
    if len(sys.argv) > 1:
        if sys.argv[1] == "manpage":
            _generate_manpage_section()
            sys.exit()
        if sys.argv[1] == "rst":
            _print_rst_section()
            sys.exit()

    raise ValueError("call the script with one of: " + " ".join(VALID_TARGETS))
