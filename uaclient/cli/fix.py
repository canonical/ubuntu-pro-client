import re

from uaclient import exceptions, security
from uaclient.cli.constants import NAME, USAGE_TMPL


def set_fix_parser(subparsers):
    parser_fix = subparsers.add_parser(
        "fix",
        help="check for and mitigate the impact of a CVE/USN on this system",
    )
    parser_fix.set_defaults(action=action_fix)
    fix_parser(parser_fix)


def fix_parser(parser):
    """Build or extend an arg parser for fix subcommand."""
    parser.usage = USAGE_TMPL.format(
        name=NAME, command="fix <CVE-yyyy-nnnn+>|<USN-nnnn-d+>"
    )
    parser.prog = "fix"
    parser.description = (
        "Inspect and resolve CVEs and USNs (Ubuntu Security Notices) on this"
        " machine."
    )
    parser._optionals.title = "Flags"
    parser.add_argument(
        "security_issue",
        help=(
            "Security vulnerability ID to inspect and resolve on this system."
            " Format: CVE-yyyy-nnnn, CVE-yyyy-nnnnnnn or USN-nnnn-dd"
        ),
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help=(
            "If used, fix will not actually run but will display"
            " everything that will happen on the machine during the"
            " command."
        ),
    )
    parser.add_argument(
        "--no-related",
        action="store_true",
        help=(
            "If used, when fixing a USN, the command will not try to"
            " also fix related USNs to the target USN."
        ),
    )

    return parser


def action_fix(args, *, cfg, **kwargs):
    if not re.match(security.CVE_OR_USN_REGEX, args.security_issue):
        raise exceptions.InvalidSecurityIssueIdFormat(
            issue=args.security_issue
        )

    fix_status = security.fix_security_issue_id(
        cfg=cfg,
        issue_id=args.security_issue,
        dry_run=args.dry_run,
        no_related=args.no_related,
    )
    return fix_status.exit_code
