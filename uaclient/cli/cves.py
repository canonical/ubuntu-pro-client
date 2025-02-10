import sys

from uaclient import exceptions, messages
from uaclient.api.u.pro.security.cves.v1 import CVEsOptions, _cves
from uaclient.cli import cli_util
from uaclient.cli.commands import ProArgument, ProArgumentGroup, ProCommand
from uaclient.cli.formatter import Table, create_link
from uaclient.cli.parser import HelpCategory
from uaclient.config import UAConfig


@cli_util.with_spinner(msg=messages.CLI_CVES_SPINNER_MSG)
def _get_cve_vulnerabilities(args, *, cfg: UAConfig, **kwargs):
    cve_options = CVEsOptions(
        fixable=args.fixable,
        unfixable=args.unfixable,
    )
    return _cves(options=cve_options, cfg=cfg)


def _get_cve_table_rows(cve_vulnerabilities):
    rows = []

    for package_name, package_info in cve_vulnerabilities.packages.items():
        for cve in package_info.cves:
            cve_info = cve_vulnerabilities.cves.get(cve.name)

            if cve_info:
                rows.append(
                    (
                        package_name,
                        cve_info.priority,
                        cve.fix_origin or "-",
                        cve.name,
                    )
                )

    return rows


def _format_cve_rows(cve_rows):
    formatted_rows = []
    for row in sorted(
        cve_rows,
        key=lambda row: (
            row[0],
            ("critical", "high", "medium", "low", "negligible").index(row[1]),
        ),
    ):
        formatted_rows.append(
            (
                row[0],
                cli_util.colorize_priority(row[1]),
                row[2],
                create_link(
                    text=row[3],
                    url="https://ubuntu.com/security/{}".format(row[3]),
                ),
            )
        )

    return formatted_rows


def _list_cves(args, cfg: UAConfig):
    cve_vulnerabilities = _get_cve_vulnerabilities(args, cfg=cfg)

    if cve_vulnerabilities.packages:
        rows = _format_cve_rows(_get_cve_table_rows(cve_vulnerabilities))

        if rows:
            print(
                Table(
                    headers=["Package", "Priority", "Origin", "Vulnerability"],
                    rows=rows,
                )
            )
        else:
            if args.unfixable:
                print(messages.CLI_UNFIXABLE_CVES_NOT_AFFECTED)
            elif args.fixable:
                print(messages.CLI_FIXABLE_CVES_NOT_AFFECTED)
            else:
                print(messages.CLI_CVES_NOT_AFFECTED)
    else:
        if args.unfixable:
            print(messages.CLI_UNFIXABLE_CVES_NOT_AFFECTED)
        elif args.fixable:
            print(messages.CLI_FIXABLE_CVES_NOT_AFFECTED)
        else:
            print(messages.CLI_CVES_NOT_AFFECTED)


def action_cves(args, *, cfg: UAConfig, **kwargs):
    if args.unfixable and args.fixable:
        raise exceptions.InvalidOptionCombination(
            option1="unfixable", option2="fixable"
        )

    try:
        _list_cves(args=args, cfg=cfg)
    except BrokenPipeError:
        sys.stderr.close()


cves_command = ProCommand(
    "cves",
    help=messages.CLI_CVES,
    description=messages.CLI_CVES_DESC,
    action=action_cves,
    help_category=HelpCategory.SECURITY,
    preserve_description=True,
    argument_groups=[
        ProArgumentGroup(
            arguments=[
                ProArgument(
                    "--unfixable",
                    help=messages.CLI_CVES_UNFIXABLE,
                    action="store_true",
                ),
                ProArgument(
                    "--fixable",
                    help=messages.CLI_CVES_FIXABLE,
                    action="store_true",
                ),
            ]
        )
    ],
)
