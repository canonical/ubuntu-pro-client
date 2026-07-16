import sys
import textwrap
from collections import namedtuple

from uaclient import defaults, exceptions, messages, system, util
from uaclient.api.u.pro.security.cves._common.v1 import VulnerabilityData
from uaclient.api.u.pro.security.usns.v1 import USNsOptions, _usns
from uaclient.cli import cli_util
from uaclient.cli.commands import ProArgument, ProArgumentGroup, ProCommand
from uaclient.cli.formatter import Table
from uaclient.cli.parser import HelpCategory
from uaclient.config import UAConfig

USN_URL_TMPL = "https://ubuntu.com/security/notices/{}"

AffectedPackage = namedtuple(
    "AffectedPackage", ["name", "fix_status", "fix_origin", "fix_version"]
)


@cli_util.with_spinner(msg=messages.CLI_CVES_SPINNER_MSG)
def _get_usn_vulnerabilities(args, *, cfg: UAConfig, **kwargs):
    try:
        result = _usns(options=USNsOptions(), cfg=cfg)
    except exceptions.VulnerabilityDataNotFound:
        result = None

    return result


def _get_affected_pkgs(usn_vulnerabilities, usn_name):
    rows = []

    for pkg_name, pkg_info in sorted(usn_vulnerabilities.packages.items()):
        for usn in pkg_info.usns:
            if usn.name == usn_name:
                rows.append(
                    AffectedPackage(
                        name=pkg_name,
                        fix_status=usn.fix_status,
                        fix_origin=usn.fix_origin,
                        fix_version=usn.fix_version,
                    )
                )
                break

    return rows


def _format_affected_pkgs(affected_pkgs):
    formatted_rows = []

    for affected_pkg in affected_pkgs:
        if affected_pkg.fix_status == "fixed":
            formatted_rows.append(
                [
                    "{}:".format(affected_pkg.name),
                    affected_pkg.fix_status,
                    "({})".format(affected_pkg.fix_origin),
                    affected_pkg.fix_version,
                ]
            )
        else:
            formatted_rows.append(
                [
                    "{}:".format(affected_pkg.name),
                    affected_pkg.fix_status,
                    "",
                    "",
                ]
            )

    return formatted_rows


def action_usn(args, *, cfg, **kwargs):
    usn_name = args.usn.upper()
    usn_vulnerabilities = _get_usn_vulnerabilities(args, cfg=cfg)

    if not usn_vulnerabilities:
        raise exceptions.VulnerabilityDataNotFound()

    affected_pkgs_table = ""
    if usn_name not in usn_vulnerabilities.usns:
        usn_data = (
            VulnerabilityData(cfg)
            .get()
            .get("security_issues", {})
            .get("usns", {})
            .get(usn_name)
        )

        if not usn_data:
            release = system.get_release_info().release
            print(
                messages.CLI_USN_NOT_FOUND_IN_DATA.format(
                    issue=args.usn,
                    release=release,
                    url=USN_URL_TMPL.format(usn_name),
                ),
                file=sys.stderr,
            )
            return

        published_at = usn_data.get("published_at")
        usn_info = {
            "title": usn_data.get("title", ""),
            "description": usn_data.get("description", ""),
            "published_at": (
                util.parse_rfc3339_date(published_at) if published_at else None
            ),
            "priority": None,
            "related_cves": usn_data.get("related_cves", []),
        }
    else:
        info = usn_vulnerabilities.usns[usn_name]
        usn_info = {
            "title": info.title,
            "description": info.description,
            "published_at": info.published_at,
            "updated_at": info.updated_at,
            "priority": info.priority,
            "related_cves": info.related_cves or [],
            "superseded_by": info.superseded_by,
        }

        affected_pkgs_rows = _format_affected_pkgs(
            _get_affected_pkgs(usn_vulnerabilities, usn_name)
        )
        affected_pkgs_table = Table(rows=affected_pkgs_rows).to_string()

    print("name:            {}".format(usn_name))
    print("public-url:      {}".format(USN_URL_TMPL.format(usn_name)))
    if usn_info.get("title"):
        print("title:           {}".format(usn_info["title"]))
    if usn_info.get("published_at"):
        print(
            "published-at:    {}".format(
                usn_info["published_at"].strftime("%Y-%m-%d")
            )
        )
    if usn_info.get("updated_at"):
        print(
            "updated-at:      {}".format(
                usn_info["updated_at"].strftime("%Y-%m-%d")
            )
        )
    if usn_info.get("superseded_by"):
        print("superseded-by:   {}".format(usn_info["superseded_by"]))
    if usn_info.get("priority"):
        print(
            "priority:        {}".format(
                cli_util.colorize_priority(usn_info["priority"])
            )
        )

    if usn_info.get("description"):
        print("description: |")
        print(
            "{}".format(
                "\n".join(
                    textwrap.wrap(
                        usn_info["description"],
                        width=defaults.PRINT_WRAP_WIDTH,
                        break_long_words=False,
                        break_on_hyphens=False,
                        initial_indent="  ",
                        subsequent_indent="  ",
                    )
                )
            )
        )

    if usn_info.get("related_cves"):
        print("related_cves:")
        for related_cve in usn_info["related_cves"]:
            print("  - {}".format(related_cve))

    if affected_pkgs_table:
        print("affected_packages:")
        for line in affected_pkgs_table.splitlines():
            print("  " + line)
    else:
        print("affected_packages: []")


usn_command = ProCommand(
    "usn",
    help=messages.CLI_USN,
    description=messages.CLI_USN_DESC,
    action=action_usn,
    help_category=HelpCategory.SECURITY,
    preserve_description=True,
    argument_groups=[
        ProArgumentGroup(
            arguments=[
                ProArgument(
                    "usn",
                    help=messages.CLI_USN_ISSUE,
                ),
            ]
        )
    ],
)
