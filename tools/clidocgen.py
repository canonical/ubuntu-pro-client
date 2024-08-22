"""
Generate RST documentation for an ubuntu-pro-client cli commands.
"""

import sys

sys.path.insert(0, ".")

from uaclient.cli import COMMANDS, get_parser
from uaclient.cli.commands import ProCommand

MANPAGE_TEMPLATE = """\
.TP
.BR "{name}" " {usage_options}"
{description}

"""


def _build_manpage_entry(command: ProCommand) -> str:
    # the usage line looks like
    # usage: <prog> <options>
    # we wanto only the <options>
    options_line = command.parser.format_usage().split(command.parser.prog)[1]
    # Remove extra spaces and eventual newlines
    usage_options = " ".join(options_line.split())

    return MANPAGE_TEMPLATE.format(
        name=command.name,
        usage_options=usage_options,
        description=command.description,
    )


if __name__ == "__main__":
    # get a parser so we register all the commands
    _parser = get_parser()

    result = ""
    for command in COMMANDS:
        result += _build_manpage_entry(command)

    print(result)
