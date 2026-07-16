import sys

from uaclient import exceptions, messages
from uaclient.api.u.pro.security.usns.v1 import USNsOptions, _usns
from uaclient.cli import cli_util
from uaclient.cli.commands import ProArgument, ProArgumentGroup, ProCommand
from uaclient.cli.formatter import Table, create_link
from uaclient.cli.parser import HelpCategory
from uaclient.config import UAConfig

# Ubuntu priorities ordered from most to least severe. USNs whose priority
# cannot be derived (no related CVE priority) sort last.
_PRIORITY_ORDER = ("critical", "high", "medium", "low", "negligible")


def _priority_sort_key(priority):
    try:
        return _PRIORITY_ORDER.index(priority)
    except ValueError:
        return len(_PRIORITY_ORDER)


@cli_util.with_spinner(msg=messages.CLI_CVES_SPINNER_MSG)
def _get_usn_vulnerabilities(args, *, cfg: UAConfig, **kwargs):
    usn_options = USNsOptions(
        fixable=args.fixable,
        unfixable=args.unfixable,
    )

    try:
        result = _usns(options=usn_options, cfg=cfg)
    except exceptions.VulnerabilityDataNotFound:
        result = None

    return result


def _get_usn_table_rows(usn_vulnerabilities):
    rows = []

    for package_name, package_info in usn_vulnerabilities.packages.items():
        for usn in package_info.usns:
            usn_info = usn_vulnerabilities.usns.get(usn.name)

            if usn_info:
                rows.append(
                    (
                        package_name,
                        usn_info.priority or "unknown",
                        usn.fix_origin or "-",
                        usn.name,
                    )
                )

    return rows


def _format_usn_rows(usn_rows):
    formatted_rows = []
    for row in sorted(
        usn_rows,
        key=lambda row: (row[0], _priority_sort_key(row[1])),
    ):
        formatted_rows.append(
            (
                row[0],
                cli_util.colorize_priority(row[1]),
                row[2],
                create_link(
                    text=row[3],
                    url="https://ubuntu.com/security/notices/{}".format(
                        row[3]
                    ),
                ),
            )
        )

    return formatted_rows


def _list_usns(args, cfg: UAConfig):
    usn_vulnerabilities = _get_usn_vulnerabilities(args, cfg=cfg)

    if not usn_vulnerabilities:
        raise exceptions.VulnerabilityDataNotFound()

    rows = _format_usn_rows(_get_usn_table_rows(usn_vulnerabilities))

    if rows:
        print(
            Table(
                headers=["Package", "Priority", "Origin", "Vulnerability"],
                rows=rows,
            )
        )
    else:
        if args.unfixable:
            print(messages.CLI_UNFIXABLE_USNS_NOT_AFFECTED)
        elif args.fixable:
            print(messages.CLI_FIXABLE_USNS_NOT_AFFECTED)
        else:
            print(messages.CLI_USNS_NOT_AFFECTED)


def action_usns(args, *, cfg: UAConfig, **kwargs):
    if args.unfixable and args.fixable:
        raise exceptions.InvalidOptionCombination(
            option1="unfixable", option2="fixable"
        )

    try:
        _list_usns(args=args, cfg=cfg)
    except BrokenPipeError:
        sys.stderr.close()


usns_command = ProCommand(
    "usns",
    help=messages.CLI_USNS,
    description=messages.CLI_USNS_DESC,
    action=action_usns,
    help_category=HelpCategory.SECURITY,
    preserve_description=True,
    argument_groups=[
        ProArgumentGroup(
            arguments=[
                ProArgument(
                    "--unfixable",
                    help=messages.CLI_USNS_UNFIXABLE,
                    action="store_true",
                ),
                ProArgument(
                    "--fixable",
                    help=messages.CLI_USNS_FIXABLE,
                    action="store_true",
                ),
            ]
        )
    ],
)
