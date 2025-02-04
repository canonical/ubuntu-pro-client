import textwrap
from collections import namedtuple

from uaclient import defaults, messages, system, util
from uaclient.api.u.pro.security.cves._common.v1 import VulnerabilityData
from uaclient.api.u.pro.security.cves.v1 import CVEInfo, CVEsOptions, _cves
from uaclient.api.u.pro.security.fix._common import (
    query_installed_source_pkg_versions,
)
from uaclient.cli import cli_util
from uaclient.cli.commands import ProArgument, ProArgumentGroup, ProCommand
from uaclient.cli.formatter import Table
from uaclient.config import UAConfig

AffectedPackage = namedtuple(
    "AffectedPackage", ["name", "fix_status", "fix_origin", "fix_version"]
)


@cli_util.with_spinner(msg=messages.CLI_CVES_SPINNER_MSG)
def _get_cve_vulnerabilities(args, *, cfg: UAConfig, **kwargs):
    return _cves(options=CVEsOptions(), cfg=cfg)


def _get_affected_pkgs(cve_vulnerabilities, cve_info, cve_name):
    rows = []
    installed_pkgs_by_source = query_installed_source_pkg_versions()

    for source_pkg in cve_info.related_packages:
        binary_pkgs = installed_pkgs_by_source.get(source_pkg, {}).keys()

        for binary_pkg in sorted(binary_pkgs):
            binary_pkg_info = cve_vulnerabilities.packages.get(binary_pkg)

            if binary_pkg_info:
                for cve in binary_pkg_info.cves:
                    if cve.name == cve_name:
                        rows.append(
                            AffectedPackage(
                                name=binary_pkg,
                                fix_status=cve.fix_status,
                                fix_origin=cve.fix_origin,
                                fix_version=cve.fix_version,
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


def action_cve(args, *, cfg, **kwargs):
    cve_name = args.cve.upper()
    cve_vulnerabilities = _get_cve_vulnerabilities(args, cfg=cfg)

    if cve_name not in cve_vulnerabilities.cves:
        cve_data = (
            VulnerabilityData(cfg)
            .get()
            .get("security_issues", {})
            .get("cves", {})
            .get(cve_name)
        )

        if not cve_data:
            series = system.get_release_info().series
            print(
                messages.CLI_CVE_NOT_FOUND_IN_DATA.format(
                    issue=args.cve,
                    series=series,
                    url="{}/{}".format(defaults.BASE_SECURITY_URL, cve_name),
                )
            )
            return

        cve_info = CVEInfo(
            description=cve_data["description"],
            published_at=util.parse_rfc3339_date(cve_data["published_at"]),
            priority=cve_data["ubuntu_priority"],
            notes=cve_data["notes"],
            cvss_score=cve_data["cvss_score"],
            cvss_severity=cve_data["cvss_severity"],
            related_usns=[],
        )
        affected_pkgs_table = ""
    else:
        cve_info = cve_vulnerabilities.cves[cve_name]

        affected_pkgs_rows = _format_affected_pkgs(
            _get_affected_pkgs(cve_vulnerabilities, cve_info, args.cve)
        )
        affected_pkgs_table = Table(rows=affected_pkgs_rows).to_string()

    print("name:            {}".format(cve_name))
    print(
        "public-url:      {}/{}".format(defaults.BASE_SECURITY_URL, cve_name)
    )
    print(
        "published-at:    {}".format(
            cve_info.published_at.strftime("%Y-%m-%d")
        )
    )
    print(
        "cve-cache-date:  {}".format(
            cve_vulnerabilities.vulnerability_data_published_at.strftime(
                "%Y-%m-%d"
            )
        )
    )
    print(
        "apt-cache-date:  {}".format(
            cve_vulnerabilities.apt_updated_at.strftime("%Y-%m-%d")
        )
    )
    print(
        "priority:        {}".format(
            cli_util.colorize_priority(cve_info.priority)
        )
    )

    if cve_info.cvss_score:
        print("cvss-score:      {}".format(cve_info.cvss_score))

    if cve_info.cvss_severity:
        print("cvss-severity:   {}".format(cve_info.cvss_severity))

    print("description: |")
    print(
        "{}".format(
            "\n".join(
                textwrap.wrap(
                    cve_info.description,
                    width=defaults.PRINT_WRAP_WIDTH,
                    break_long_words=False,
                    break_on_hyphens=False,
                    initial_indent="  ",
                    subsequent_indent="  ",
                )
            )
        )
    )

    if cve_info.notes:
        print("notes:")
        for note in cve_info.notes:
            print(
                textwrap.fill(
                    note,
                    width=defaults.PRINT_WRAP_WIDTH,
                    break_long_words=False,
                    break_on_hyphens=False,
                    initial_indent="  - ",
                    subsequent_indent="    ",
                )
            )

    if affected_pkgs_table:
        print("affected_packages:")
        for line in affected_pkgs_table.splitlines():
            print("  " + line)
    else:
        print("affected_packages: []")

    if cve_info.related_usns:
        related_usns = [
            "  {}: {}".format(usn.name, usn.title)
            for usn in cve_info.related_usns
            if usn.title
        ]

        if related_usns:
            print("related_usns:")
            for related_usn in related_usns:
                print(related_usn)


cve_command = ProCommand(
    "cve",
    help=messages.CLI_CVE,
    description=messages.CLI_CVE_DESC,
    action=action_cve,
    preserve_description=True,
    argument_groups=[
        ProArgumentGroup(
            arguments=[
                ProArgument(
                    "cve",
                    help=messages.CLI_CVE_ISSUE,
                ),
            ]
        )
    ],
)
