#!/usr/bin/python3
"""
Generate documentation for an ubuntu-pro-client cli commands.
"""

import sys

sys.path.insert(0, ".")

from uaclient.cli import COMMANDS, get_parser
from uaclient.cli.commands import ProCommand

VALID_TARGETS = ["manpage"]

MANPAGE_TEMPLATE = """\
.TP
.BR "{indent}{name}" " {usage_options}"
{description}

"""


def _build_manpage_entry(command: ProCommand, indent: str = "") -> str:
    # the usage line looks like
    # usage: <prog> <options>
    # we wanto only the <options>
    options_line = command.parser.format_usage().split(command.parser.prog)[1]
    # Remove extra spaces and eventual newlines
    usage_options = " ".join(options_line.split())

    return MANPAGE_TEMPLATE.format(
        indent=indent,
        name=command.name,
        usage_options=usage_options,
        description=command.description,
    )


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

    raise ValueError("call the script with one of: " + " ".join(VALID_TARGETS))
