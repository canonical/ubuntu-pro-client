import contextlib
import io
import textwrap

import mock
import pytest

from uaclient import exceptions, messages
from uaclient.api.u.pro.security.fix._common import FixStatus, UnfixedPackage
from uaclient.api.u.pro.security.fix._common.plan.v1 import (
    ESM_APPS_POCKET,
    ESM_INFRA_POCKET,
    STANDARD_UPDATES_POCKET,
    AptUpgradeData,
    AttachData,
    EnableData,
    FailUpdatingESMCacheData,
    FixPlanAptUpgradeStep,
    FixPlanAttachStep,
    FixPlanEnableStep,
    FixPlanNoOpLivepatchFixStep,
    FixPlanNoOpStatus,
    FixPlanNoOpStep,
    FixPlanResult,
    FixPlanUSNResult,
    FixPlanWarningFailUpdatingESMCache,
    FixPlanWarningPackageCannotBeInstalled,
    FixPlanWarningSecurityIssueNotFixed,
    NoOpData,
    NoOpLivepatchFixData,
    PackageCannotBeInstalledData,
    SecurityIssueNotFixedData,
    USNAdditionalData,
)
from uaclient.api.u.pro.security.fix.usn.plan.v1 import (
    USNFixPlanResult,
    USNSFixPlanResult,
)
from uaclient.cli import main
from uaclient.cli.fix import (
    FixContext,
    _execute_apt_upgrade_step,
    _execute_attach_step,
    _execute_enable_step,
    _handle_subscription_for_required_service,
    _perform_magic_attach,
    action_fix,
    execute_fix_plan,
    fix_usn,
    print_cve_header,
    print_usn_header,
)
from uaclient.entitlements.entitlement_status import (
    ApplicabilityStatus,
    UserFacingStatus,
)
from uaclient.files.notices import Notice
from uaclient.status import colorize_commands

M_PATH = "uaclient.cli.fix."

HELP_OUTPUT = textwrap.dedent(
    """\
usage: pro fix <CVE-yyyy-nnnn+>|<USN-nnnn-d+> [flags]

Inspect and resolve CVEs and USNs (Ubuntu Security Notices) on this machine.

positional arguments:
  security_issue  Security vulnerability ID to inspect and resolve on this
                  system. Format: CVE-yyyy-nnnn, CVE-yyyy-nnnnnnn or USN-nnnn-
                  dd

Flags:
  -h, --help      show this help message and exit
  --dry-run       If used, fix will not actually run but will display
                  everything that will happen on the machine during the
                  command.
  --no-related    If used, when fixing a USN, the command will not try to also
                  fix related USNs to the target USN.
"""
)


class TestActionFix:
    @mock.patch("uaclient.log.setup_cli_logging")
    @mock.patch("uaclient.cli.contract.get_available_resources")
    def test_fix_help(
        self, _m_resources, _m_setup_logging, capsys, FakeConfig
    ):
        with pytest.raises(SystemExit):
            with mock.patch("sys.argv", ["/usr/bin/ua", "fix", "--help"]):
                with mock.patch(
                    "uaclient.config.UAConfig",
                    return_value=FakeConfig(),
                ):
                    main()
        out, _err = capsys.readouterr()
        assert HELP_OUTPUT == out

    @pytest.mark.parametrize(
        "issue,is_valid",
        (
            ("CVE-2020-1234", True),
            ("cve-2020-12345", True),
            ("cve-1234-123456", True),
            ("CVE-2020-1234567", True),
            ("USN-1234-1", True),
            ("usn-1234-12", True),
            ("USN-12345-1", True),
            ("usn-12345-12", True),
            ("lsn-1234-1", True),
            ("LSN-1234-12", True),
            ("LSN-1234-123", False),
            ("cve-1234-123", False),
            ("CVE-1234-12345678", False),
            ("USA-1234-12345678", False),
        ),
    )
    @mock.patch("uaclient.cli.fix.fix_cve")
    @mock.patch("uaclient.cli.fix.fix_usn")
    def test_attached(self, m_fix_cve, m_fix_usn, issue, is_valid, FakeConfig):
        """Check that root and non-root will emit attached status"""
        cfg = FakeConfig()
        args = mock.MagicMock(
            security_issue=issue, dry_run=False, no_related=False
        )
        m_fix_cve.return_value = FixStatus.SYSTEM_NON_VULNERABLE
        m_fix_usn.return_value = FixStatus.SYSTEM_NON_VULNERABLE
        if is_valid:
            assert 0 == action_fix(args, cfg=cfg)
        else:
            with pytest.raises(exceptions.UbuntuProError) as excinfo:
                action_fix(args, cfg=cfg)

            expected_msg = (
                'Error: issue "{}" is not recognized.\n'
                'Usage: "pro fix CVE-yyyy-nnnn" or "pro fix USN-nnnn"'
            ).format(issue)

            assert expected_msg == str(excinfo.value)
            assert 0 == m_fix_cve.call_count
            assert 0 == m_fix_usn.call_count

    def test_cve_header(self):
        cve = FixPlanResult(
            title="CVE-2020-1472",
            description="Samba vulnerability",
            expected_status=FixStatus.SYSTEM_NON_VULNERABLE.value.msg,
            affected_packages=["pkg1", "pkg2"],
            plan=[],
            warnings=None,
            error=None,
            additional_data=None,
        )

        fake_stdout = io.StringIO()
        with contextlib.redirect_stdout(fake_stdout):
            print_cve_header(cve)

        assert (
            textwrap.dedent(
                """\
                CVE-2020-1472: Samba vulnerability
                 - https://ubuntu.com/security/CVE-2020-1472"""
            )
            == fake_stdout.getvalue().strip()
        )

    @pytest.mark.parametrize(
        "usn,expected_output",
        (
            (
                FixPlanUSNResult(
                    target_usn_plan=FixPlanResult(
                        title="USN-4510-2",
                        description="Samba vulnerability",
                        expected_status=FixStatus.SYSTEM_NON_VULNERABLE.value.msg,  # noqa
                        affected_packages=["pkg1", "pkg2"],
                        plan=[],
                        warnings=None,
                        error=None,
                        additional_data=USNAdditionalData(
                            associated_cves=["CVE-2020-1473", "CVE-2020-1472"],
                            associated_launchpad_bugs=[],
                        ),
                    ),
                    related_usns_plan=[],
                ),
                textwrap.dedent(
                    """\
                    USN-4510-2: Samba vulnerability
                    Associated CVEs:
                     - https://ubuntu.com/security/CVE-2020-1473
                     - https://ubuntu.com/security/CVE-2020-1472"""
                ),
            ),
            (
                FixPlanUSNResult(
                    target_usn_plan=FixPlanResult(
                        title="USN-4038-3",
                        description="USN vulnerability",
                        expected_status=FixStatus.SYSTEM_NON_VULNERABLE.value.msg,  # noqa
                        affected_packages=["pkg1", "pkg2"],
                        plan=[],
                        warnings=None,
                        error=None,
                        additional_data=USNAdditionalData(
                            associated_cves=[],
                            associated_launchpad_bugs=[
                                "https://launchpad.net/bugs/1834494"
                            ],
                        ),
                    ),
                    related_usns_plan=[],
                ),
                textwrap.dedent(
                    """\
                    USN-4038-3: USN vulnerability
                    Found Launchpad bugs:
                     - https://launchpad.net/bugs/1834494"""
                ),
            ),
        ),
    )
    def test_usn_header(self, usn, expected_output):
        fake_stdout = io.StringIO()
        with contextlib.redirect_stdout(fake_stdout):
            print_usn_header(usn)
        assert expected_output == fake_stdout.getvalue().strip()


class TestExecuteFixPlan:
    @pytest.mark.parametrize(
        "fix_plan,dry_run,cloud_type,expected_output,"
        "expected_fix_status,expected_unfixed_pkgs",
        (
            (  # No affected_packages listed
                FixPlanResult(
                    title="USN-###",
                    description="test",
                    expected_status=FixStatus.SYSTEM_NOT_AFFECTED.value.msg,
                    affected_packages=[],
                    plan=[
                        FixPlanNoOpStep(
                            data=NoOpData(
                                status=FixPlanNoOpStatus.NOT_AFFECTED.value
                            ),
                            order=1,
                        )
                    ],
                    warnings=[],
                    error=None,
                    additional_data=None,
                ),
                False,
                (None, None),
                textwrap.dedent(
                    """\
                   No affected source packages are installed.

                   {check} USN-### does not affect your system.
                   """.format(
                        check=messages.OKGREEN_CHECK  # noqa: E126
                    )  # noqa: E126
                ),
                FixStatus.SYSTEM_NOT_AFFECTED,
                [],
            ),
            (  # CVE already fixed by Livepatch
                FixPlanResult(
                    title="CVE-###",
                    description="test",
                    expected_status=FixStatus.SYSTEM_NOT_AFFECTED.value.msg,
                    affected_packages=[],
                    plan=[
                        FixPlanNoOpLivepatchFixStep(
                            data=NoOpLivepatchFixData(
                                status="cve-fixed-by-livepatch",
                                patch_version="87.1",
                            ),
                            order=1,
                        )
                    ],
                    warnings=[],
                    error=None,
                    additional_data=None,
                ),
                False,
                (None, None),
                messages.CVE_FIXED_BY_LIVEPATCH.format(
                    issue="CVE-###",
                    version="87.1",
                ),
                FixStatus.SYSTEM_NON_VULNERABLE,
                [],
            ),
            (  # version is >= released affected package
                FixPlanResult(
                    title="USN-###",
                    description="test",
                    expected_status=FixStatus.SYSTEM_NON_VULNERABLE.value.msg,
                    affected_packages=["slsrc"],
                    plan=[
                        FixPlanAptUpgradeStep(
                            data=AptUpgradeData(
                                binary_packages=[],
                                source_packages=["slsrc"],
                                pocket=STANDARD_UPDATES_POCKET,
                            ),
                            order=1,
                        )
                    ],
                    warnings=[],
                    error=None,
                    additional_data=None,
                ),
                False,
                (None, None),
                textwrap.dedent(
                    """\
                   1 affected source package is installed: slsrc
                   (1/1) slsrc:
                   A fix is available in Ubuntu standard updates.
                   The update is already installed.

                   {check} USN-### is resolved.
                   """.format(
                        check=messages.OKGREEN_CHECK  # noqa: E126
                    )  # noqa: E126
                ),
                FixStatus.SYSTEM_NON_VULNERABLE,
                [],
            ),
            (  # installing package fix
                FixPlanResult(
                    title="USN-###",
                    description="test",
                    expected_status=FixStatus.SYSTEM_NON_VULNERABLE.value.msg,
                    affected_packages=["slsrc"],
                    plan=[
                        FixPlanAptUpgradeStep(
                            data=AptUpgradeData(
                                binary_packages=["sl"],
                                source_packages=["slsrc"],
                                pocket=STANDARD_UPDATES_POCKET,
                            ),
                            order=1,
                        )
                    ],
                    warnings=[],
                    error=None,
                    additional_data=None,
                ),
                False,
                (None, None),
                textwrap.dedent(
                    """\
                   1 affected source package is installed: slsrc
                   (1/1) slsrc:
                   A fix is available in Ubuntu standard updates.
                   """
                )
                + colorize_commands(
                    [["apt update && apt install --only-upgrade" " -y sl"]]
                )
                + "\n\n"
                + "{check} USN-### is resolved.\n".format(
                    check=messages.OKGREEN_CHECK
                ),
                FixStatus.SYSTEM_NON_VULNERABLE,
                [],
            ),
            (  # installing package fix that comes from esm-infra
                FixPlanResult(
                    title="USN-###",
                    description="test",
                    expected_status=FixStatus.SYSTEM_NON_VULNERABLE.value.msg,
                    affected_packages=["slsrc"],
                    plan=[
                        FixPlanAttachStep(
                            data=AttachData(
                                reason="test",
                                required_service=ESM_INFRA_POCKET,
                                source_packages=["slsrc"],
                            ),
                            order=1,
                        ),
                        FixPlanEnableStep(
                            data=EnableData(
                                service=ESM_INFRA_POCKET,
                                source_packages=["slsrc"],
                            ),
                            order=2,
                        ),
                        FixPlanAptUpgradeStep(
                            data=AptUpgradeData(
                                binary_packages=["sl"],
                                source_packages=["slsrc"],
                                pocket=ESM_INFRA_POCKET,
                            ),
                            order=3,
                        ),
                    ],
                    warnings=[],
                    error=None,
                    additional_data=None,
                ),
                False,
                ("azure", None),
                textwrap.dedent(
                    """\
                    1 affected source package is installed: slsrc
                    (1/1) slsrc:
                    A fix is available in Ubuntu Pro: ESM Infra.
                    """
                )
                + "\n".join(
                    [
                        messages.SECURITY_USE_PRO_TMPL.format(
                            title="Azure",
                            cloud_specific_url="https://ubuntu.com/azure/pro",
                        ),
                        messages.SECURITY_UPDATE_NOT_INSTALLED_SUBSCRIPTION,
                    ]
                ),
                FixStatus.SYSTEM_STILL_VULNERABLE,
                [
                    UnfixedPackage(
                        pkg="slsrc",
                        unfixed_reason=messages.SECURITY_UA_SERVICE_REQUIRED.format(  # noqa
                            service="esm-infra"
                        ),
                    )
                ],
            ),
            (  # installing package fixes that comes from
                # standard-updates and esm-infra
                FixPlanResult(
                    title="USN-###",
                    description="test",
                    expected_status=FixStatus.SYSTEM_NON_VULNERABLE.value.msg,
                    affected_packages=["curl", "slsrc"],
                    plan=[
                        FixPlanAptUpgradeStep(
                            data=AptUpgradeData(
                                binary_packages=["curl"],
                                source_packages=["curl"],
                                pocket=STANDARD_UPDATES_POCKET,
                            ),
                            order=1,
                        ),
                        FixPlanAttachStep(
                            data=AttachData(
                                reason="test",
                                required_service=ESM_APPS_POCKET,
                                source_packages=["slsrc"],
                            ),
                            order=2,
                        ),
                        FixPlanEnableStep(
                            data=EnableData(
                                service=ESM_APPS_POCKET,
                                source_packages=["slsrc"],
                            ),
                            order=3,
                        ),
                        FixPlanAptUpgradeStep(
                            data=AptUpgradeData(
                                binary_packages=["sl"],
                                source_packages=["slsrc"],
                                pocket=ESM_APPS_POCKET,
                            ),
                            order=4,
                        ),
                    ],
                    warnings=[],
                    error=None,
                    additional_data=None,
                ),
                False,
                ("gce", None),
                textwrap.dedent(
                    """\
                    2 affected source packages are installed: curl, slsrc
                    (1/2) curl:
                    A fix is available in Ubuntu standard updates.
                    """
                )
                + colorize_commands(
                    [["apt update && apt install --only-upgrade" " -y curl"]]
                )
                + "\n"
                + textwrap.dedent(
                    """\
                    (2/2) slsrc:
                    A fix is available in Ubuntu Pro: ESM Apps.
                    """
                )
                + "\n".join(
                    [
                        messages.SECURITY_USE_PRO_TMPL.format(
                            title="GCP",
                            cloud_specific_url="https://ubuntu.com/gcp/pro",
                        ),
                        messages.SECURITY_UPDATE_NOT_INSTALLED_SUBSCRIPTION,
                    ]
                )
                + "\n\n"
                + "1 package is still affected: slsrc",
                FixStatus.SYSTEM_STILL_VULNERABLE,
                [
                    UnfixedPackage(
                        pkg="slsrc",
                        unfixed_reason=messages.SECURITY_UA_SERVICE_REQUIRED.format(  # noqa
                            service="esm-apps"
                        ),
                    )
                ],
            ),
            (  # installing package fix that are not yet available
                FixPlanResult(
                    title="USN-###",
                    description="test",
                    expected_status=FixStatus.SYSTEM_NON_VULNERABLE.value.msg,
                    affected_packages=[
                        "pkg1",
                        "pkg2",
                        "pkg3",
                        "pkg4",
                        "pkg5",
                        "pkg6",
                        "pkg7",
                        "pkg8",
                        "pkg9",
                        "pkg10",
                        "pkg11",
                        "pkg12",
                        "pkg13",
                        "pkg14",
                        "pkg15",
                    ],
                    plan=[
                        FixPlanAptUpgradeStep(
                            data=AptUpgradeData(
                                binary_packages=["pkg10", "pkg11"],
                                source_packages=["pkg10", "pkg11"],
                                pocket=STANDARD_UPDATES_POCKET,
                            ),
                            order=5,
                        ),
                        FixPlanAttachStep(
                            data=AttachData(
                                reason="test",
                                required_service=ESM_INFRA_POCKET,
                                source_packages=["pkg12", "pkg13"],
                            ),
                            order=6,
                        ),
                        FixPlanEnableStep(
                            data=EnableData(
                                service=ESM_INFRA_POCKET,
                                source_packages=["pkg12", "pkg13"],
                            ),
                            order=7,
                        ),
                        FixPlanAptUpgradeStep(
                            data=AptUpgradeData(
                                binary_packages=["pkg12", "pkg13"],
                                source_packages=["pkg12", "pkg13"],
                                pocket=ESM_INFRA_POCKET,
                            ),
                            order=8,
                        ),
                        FixPlanAptUpgradeStep(
                            data=AptUpgradeData(
                                binary_packages=["pkg14", "pkg15"],
                                source_packages=["pkg14", "pkg15"],
                                pocket=ESM_APPS_POCKET,
                            ),
                            order=9,
                        ),
                    ],
                    warnings=[
                        FixPlanWarningSecurityIssueNotFixed(
                            data=SecurityIssueNotFixedData(
                                source_packages=["pkg1", "pkg2", "pkg9"],
                                status="ignored",
                            ),
                            order=1,
                        ),
                        FixPlanWarningSecurityIssueNotFixed(
                            data=SecurityIssueNotFixedData(
                                source_packages=["pkg7", "pkg8"],
                                status="needed",
                            ),
                            order=2,
                        ),
                        FixPlanWarningSecurityIssueNotFixed(
                            data=SecurityIssueNotFixedData(
                                source_packages=["pkg5", "pkg6"],
                                status="needs-triage",
                            ),
                            order=3,
                        ),
                        FixPlanWarningSecurityIssueNotFixed(
                            data=SecurityIssueNotFixedData(
                                source_packages=["pkg3", "pkg4"],
                                status="pending",
                            ),
                            order=4,
                        ),
                    ],
                    error=None,
                    additional_data=None,
                ),
                False,
                ("gce", None),
                textwrap.dedent(
                    """\
                    15 affected source packages are installed: {}
                    (1/15, 2/15, 3/15) pkg1, pkg2, pkg9:
                    Sorry, no fix is available.
                    (4/15, 5/15) pkg7, pkg8:
                    Sorry, no fix is available yet.
                    (6/15, 7/15) pkg5, pkg6:
                    Ubuntu security engineers are investigating this issue.
                    (8/15, 9/15) pkg3, pkg4:
                    A fix is coming soon. Try again tomorrow.
                    (10/15, 11/15) pkg10, pkg11:
                    A fix is available in Ubuntu standard updates.
                    """
                ).format(
                    (
                        "pkg1, pkg10, pkg11, pkg12, pkg13,\n"
                        "    pkg14, pkg15, pkg2, pkg3, pkg4, pkg5, pkg6, pkg7,"
                        " pkg8, pkg9"
                    )
                )
                + colorize_commands(
                    [
                        [
                            "apt update && apt install --only-upgrade"
                            " -y pkg10 pkg11"
                        ]
                    ]
                )
                + "\n"
                + textwrap.dedent(
                    """\
                    (12/15, 13/15) pkg12, pkg13:
                    A fix is available in Ubuntu Pro: ESM Infra.
                    """
                )
                + "\n".join(
                    [
                        messages.SECURITY_USE_PRO_TMPL.format(
                            title="GCP",
                            cloud_specific_url="https://ubuntu.com/gcp/pro",
                        ),
                        messages.SECURITY_UPDATE_NOT_INSTALLED_SUBSCRIPTION,
                    ]
                )
                + "\n\n"
                + "11 packages are still affected: {}".format(
                    (
                        "pkg1, pkg12, pkg13, pkg2, pkg3, pkg4, pkg5,\n"
                        "    pkg6, pkg7, pkg8, pkg9"
                    )
                ),
                FixStatus.SYSTEM_STILL_VULNERABLE,
                [
                    UnfixedPackage(
                        pkg="pkg1",
                        unfixed_reason=messages.SECURITY_CVE_STATUS_IGNORED,
                    ),
                    UnfixedPackage(
                        pkg="pkg2",
                        unfixed_reason=messages.SECURITY_CVE_STATUS_IGNORED,
                    ),
                    UnfixedPackage(
                        pkg="pkg9",
                        unfixed_reason=messages.SECURITY_CVE_STATUS_IGNORED,
                    ),
                    UnfixedPackage(
                        pkg="pkg7",
                        unfixed_reason=messages.SECURITY_CVE_STATUS_NEEDED,
                    ),
                    UnfixedPackage(
                        pkg="pkg8",
                        unfixed_reason=messages.SECURITY_CVE_STATUS_NEEDED,
                    ),
                    UnfixedPackage(
                        pkg="pkg5",
                        unfixed_reason=messages.SECURITY_CVE_STATUS_TRIAGE,
                    ),
                    UnfixedPackage(
                        pkg="pkg6",
                        unfixed_reason=messages.SECURITY_CVE_STATUS_TRIAGE,
                    ),
                    UnfixedPackage(
                        pkg="pkg3",
                        unfixed_reason=messages.SECURITY_CVE_STATUS_PENDING,
                    ),
                    UnfixedPackage(
                        pkg="pkg4",
                        unfixed_reason=messages.SECURITY_CVE_STATUS_PENDING,
                    ),
                    UnfixedPackage(
                        pkg="pkg12",
                        unfixed_reason=messages.SECURITY_UA_SERVICE_REQUIRED.format(  # noqa
                            service="esm-infra"
                        ),
                    ),
                    UnfixedPackage(
                        pkg="pkg13",
                        unfixed_reason=messages.SECURITY_UA_SERVICE_REQUIRED.format(  # noqa
                            service="esm-infra"
                        ),
                    ),
                ],
            ),
            (  # installing package fix that are not yet available
                FixPlanResult(
                    title="USN-###",
                    description="test",
                    expected_status=FixStatus.SYSTEM_NON_VULNERABLE.value.msg,
                    affected_packages=[
                        "longpackagename1",
                        "longpackagename2",
                        "longpackagename3",
                        "longpackagename4",
                        "longpackagename5",
                    ],
                    plan=[
                        FixPlanAptUpgradeStep(
                            data=AptUpgradeData(
                                binary_packages=[
                                    "longpackagename1",
                                    "longpackagename2",
                                    "longpackagename3",
                                    "longpackagename4",
                                    "longpackagename5",
                                ],
                                source_packages=[
                                    "longpackagename1",
                                    "longpackagename2",
                                    "longpackagename3",
                                    "longpackagename4",
                                    "longpackagename5",
                                ],
                                pocket=STANDARD_UPDATES_POCKET,
                            ),
                            order=1,
                        ),
                    ],
                    warnings=[],
                    error=None,
                    additional_data=None,
                ),
                False,
                ("gce", None),
                """\
5 affected source packages are installed: longpackagename1, longpackagename2,
    longpackagename3, longpackagename4, longpackagename5
(1/5, 2/5, 3/5, 4/5, 5/5) longpackagename1, longpackagename2, longpackagename3,
    longpackagename4, longpackagename5:
A fix is available in Ubuntu standard updates.\n"""
                + colorize_commands(
                    [
                        [
                            "apt update && apt install --only-upgrade"
                            " -y longpackagename1 longpackagename2 "
                            "longpackagename3 longpackagename4 "
                            "longpackagename5"
                        ]
                    ]
                )
                + "\n\n"
                + "{check} USN-### is resolved.\n".format(
                    check=messages.OKGREEN_CHECK
                ),
                FixStatus.SYSTEM_NON_VULNERABLE,
                [],
            ),
            (
                FixPlanResult(
                    title="USN-###",
                    description="test",
                    expected_status=FixStatus.SYSTEM_STILL_VULNERABLE.value.msg,  # noqa
                    affected_packages=["pkg1", "pkg2"],
                    plan=[
                        FixPlanAptUpgradeStep(
                            data=AptUpgradeData(
                                binary_packages=["pkg2"],
                                source_packages=["pkg2"],
                                pocket=STANDARD_UPDATES_POCKET,
                            ),
                            order=2,
                        ),
                    ],
                    warnings=[
                        FixPlanWarningPackageCannotBeInstalled(
                            data=PackageCannotBeInstalledData(
                                binary_package="pkg1",
                                binary_package_version="2.0",
                                source_package="pkg1",
                                related_source_packages=["pkg1", "pkg2"],
                                pocket=STANDARD_UPDATES_POCKET,
                            ),
                            order=1,
                        )
                    ],
                    error=None,
                    additional_data=None,
                ),
                False,
                (None, None),
                textwrap.dedent(
                    """\
                    2 affected source packages are installed: pkg1, pkg2
                    (1/2, 2/2) pkg1, pkg2:
                    A fix is available in Ubuntu standard updates.
                    - Cannot install package pkg1 version 2.0
                    """
                )
                + colorize_commands(
                    [["apt update && apt install --only-upgrade" " -y pkg2"]]
                )
                + "\n\n"
                + "1 package is still affected: pkg1"
                + "\n"
                + "{check} USN-### is not resolved.\n".format(
                    check=messages.FAIL_X
                ),
                FixStatus.SYSTEM_STILL_VULNERABLE,
                [
                    UnfixedPackage(
                        pkg="pkg1",
                        unfixed_reason="Cannot install package pkg1 version 2.0",  # noqa
                    ),
                ],
            ),
            (
                FixPlanResult(
                    title="USN-###",
                    description="test",
                    expected_status=FixStatus.SYSTEM_STILL_VULNERABLE.value.msg,  # noqa
                    affected_packages=["pkg1", "pkg2"],
                    plan=[
                        FixPlanAptUpgradeStep(
                            data=AptUpgradeData(
                                binary_packages=["pkg2"],
                                source_packages=["pkg2"],
                                pocket=STANDARD_UPDATES_POCKET,
                            ),
                            order=3,
                        ),
                    ],
                    warnings=[
                        FixPlanWarningFailUpdatingESMCache(
                            data=FailUpdatingESMCacheData(
                                title="Error msg",
                                code="error-code",
                            ),
                            order=1,
                        ),
                        FixPlanWarningPackageCannotBeInstalled(
                            data=PackageCannotBeInstalledData(
                                binary_package="pkg1",
                                binary_package_version="2.0",
                                source_package="pkg1",
                                related_source_packages=["pkg1", "pkg2"],
                                pocket=STANDARD_UPDATES_POCKET,
                            ),
                            order=2,
                        ),
                    ],
                    error=None,
                    additional_data=None,
                ),
                False,
                (None, None),
                textwrap.dedent(
                    """\
                    2 affected source packages are installed: pkg1, pkg2
                    WARNING: Failed to update ESM cache - package availability may be inaccurate
                    (1/2, 2/2) pkg1, pkg2:
                    A fix is available in Ubuntu standard updates.
                    - Cannot install package pkg1 version 2.0
                    """  # noqa
                )
                + colorize_commands(
                    [["apt update && apt install --only-upgrade" " -y pkg2"]]
                )
                + "\n\n"
                + "1 package is still affected: pkg1"
                + "\n"
                + "{check} USN-### is not resolved.\n".format(
                    check=messages.FAIL_X
                ),
                FixStatus.SYSTEM_STILL_VULNERABLE,
                [
                    UnfixedPackage(
                        pkg="pkg1",
                        unfixed_reason="Cannot install package pkg1 version 2.0",  # noqa
                    ),
                ],
            ),
        ),
    )
    @mock.patch("uaclient.system.should_reboot", return_value=False)
    @mock.patch("uaclient.cli.fix.get_cloud_type")
    @mock.patch("uaclient.util.prompt_choices", return_value="c")
    @mock.patch("uaclient.apt.run_apt_update_command")
    @mock.patch("uaclient.apt.run_apt_command")
    def test_execute_fix_plan(
        self,
        _m_apt_run_cmd,
        _m_apt_run_update,
        _m_prompt,
        m_get_cloud_type,
        _m_should_reboot,
        fix_plan,
        dry_run,
        cloud_type,
        expected_output,
        expected_fix_status,
        expected_unfixed_pkgs,
        capsys,
        FakeConfig,
    ):
        m_get_cloud_type.return_value = cloud_type
        with mock.patch("uaclient.util.sys") as m_sys:
            m_stdout = mock.MagicMock()
            type(m_sys).stdout = m_stdout
            type(m_stdout).encoding = mock.PropertyMock(return_value="utf-8")
            assert (
                expected_fix_status,
                expected_unfixed_pkgs,
            ) == execute_fix_plan(fix_plan, dry_run, cfg=FakeConfig())

        out, _ = capsys.readouterr()
        assert expected_output in out

    @pytest.mark.parametrize(
        "fix_plan,expected_output,expected_fix_status,expected_unfixed_pkgs",
        (
            (
                FixPlanResult(
                    title="USN-###",
                    description="test",
                    expected_status=FixStatus.SYSTEM_NON_VULNERABLE.value.msg,
                    affected_packages=["pkg1", "pkg2", "pkg3"],
                    plan=[
                        FixPlanAptUpgradeStep(
                            data=AptUpgradeData(
                                binary_packages=["pkg1", "pkg2", "pkg3"],
                                source_packages=["pkg1", "pkg2", "pkg3"],
                                pocket=STANDARD_UPDATES_POCKET,
                            ),
                            order=1,
                        ),
                    ],
                    warnings=[],
                    error=None,
                    additional_data=None,
                ),
                textwrap.dedent(
                    """\
                    3 affected source packages are installed: pkg1, pkg2, pkg3
                    (1/3, 2/3, 3/3) pkg1, pkg2, pkg3:
                    A fix is available in Ubuntu standard updates.
                    """
                )
                + colorize_commands(
                    [
                        [
                            "apt update && apt install --only-upgrade"
                            " -y pkg1 pkg2 pkg3"
                        ]
                    ]
                )
                + "\n"
                + "test exception"
                + "\n\n"
                + "3 packages are still affected: pkg1, pkg2, pkg3"
                + "\n"
                + "{check} USN-### is not resolved.\n".format(
                    check=messages.FAIL_X
                ),
                FixStatus.SYSTEM_STILL_VULNERABLE,
                [
                    UnfixedPackage(
                        pkg="pkg1",
                        unfixed_reason="test exception",
                    ),
                    UnfixedPackage(
                        pkg="pkg2",
                        unfixed_reason="test exception",
                    ),
                    UnfixedPackage(
                        pkg="pkg3",
                        unfixed_reason="test exception",
                    ),
                ],
            ),
        ),
    )
    @mock.patch("uaclient.system.should_reboot", return_value=False)
    @mock.patch("uaclient.apt.run_apt_update_command")
    def test_execute_fix_plan_apt_upgrade_fail(
        self,
        m_apt_update,
        _m_should_reboot,
        fix_plan,
        expected_output,
        expected_fix_status,
        expected_unfixed_pkgs,
        capsys,
        FakeConfig,
    ):
        m_apt_update.side_effect = Exception("test exception")
        with mock.patch("uaclient.util.sys") as m_sys:
            m_stdout = mock.MagicMock()
            type(m_sys).stdout = m_stdout
            type(m_stdout).encoding = mock.PropertyMock(return_value="utf-8")
            assert (
                expected_fix_status,
                expected_unfixed_pkgs,
            ) == execute_fix_plan(fix_plan, dry_run=False, cfg=FakeConfig())

        out, _ = capsys.readouterr()
        assert expected_output in out

    @pytest.mark.parametrize(
        "fix_plan,expected_output,expected_fix_status,"
        "expected_unfixed_pkgs",
        (
            (  # installing package fixes that comes from
                # standard-updates and esm-infra when attaching
                # the system
                FixPlanResult(
                    title="USN-###",
                    description="test",
                    expected_status=FixStatus.SYSTEM_NON_VULNERABLE.value.msg,
                    affected_packages=["pkg1", "pkg2", "pkg3"],
                    plan=[
                        FixPlanAptUpgradeStep(
                            data=AptUpgradeData(
                                binary_packages=["pkg2"],
                                source_packages=["pkg2"],
                                pocket=STANDARD_UPDATES_POCKET,
                            ),
                            order=1,
                        ),
                        FixPlanAttachStep(
                            data=AttachData(
                                reason="test",
                                required_service=ESM_INFRA_POCKET,
                                source_packages=["pkg3"],
                            ),
                            order=2,
                        ),
                        FixPlanEnableStep(
                            data=EnableData(
                                service=ESM_INFRA_POCKET,
                                source_packages=["pkg3"],
                            ),
                            order=3,
                        ),
                        FixPlanAptUpgradeStep(
                            data=AptUpgradeData(
                                binary_packages=["pkg3"],
                                source_packages=["pkg3"],
                                pocket=ESM_INFRA_POCKET,
                            ),
                            order=4,
                        ),
                        FixPlanEnableStep(
                            data=EnableData(
                                service=ESM_APPS_POCKET,
                                source_packages=["pkg1"],
                            ),
                            order=5,
                        ),
                        FixPlanAptUpgradeStep(
                            data=AptUpgradeData(
                                binary_packages=["pkg1"],
                                source_packages=["pkg1"],
                                pocket=ESM_APPS_POCKET,
                            ),
                            order=6,
                        ),
                    ],
                    warnings=[],
                    error=None,
                    additional_data=None,
                ),
                textwrap.dedent(
                    """\
                    3 affected source packages are installed: pkg1, pkg2, pkg3
                    (1/3) pkg2:
                    A fix is available in Ubuntu standard updates.
                    """
                )
                + colorize_commands(
                    [["apt update && apt install --only-upgrade" " -y pkg2"]]
                )
                + "\n"
                + textwrap.dedent(
                    """\
                    (2/3) pkg3:
                    A fix is available in Ubuntu Pro: ESM Infra.
                    """
                )
                + messages.SECURITY_UPDATE_NOT_INSTALLED_SUBSCRIPTION
                + "\n"
                + messages.PROMPT_ENTER_TOKEN
                + "\n"
                + colorize_commands([["pro attach pro_token"]])
                + "\n"
                + colorize_commands(
                    [["apt update && apt install --only-upgrade" " -y pkg3"]]
                )
                + "\n"
                + textwrap.dedent(
                    """\
                    (3/3) pkg1:
                    A fix is available in Ubuntu Pro: ESM Apps.
                    """
                )
                + colorize_commands(
                    [["apt update && apt install --only-upgrade" " -y pkg1"]]
                )
                + "\n\n"
                + "{check} USN-### is resolved.\n".format(
                    check=messages.OKGREEN_CHECK
                ),
                FixStatus.SYSTEM_NON_VULNERABLE,
                [],
            ),
        ),
    )
    @mock.patch("uaclient.apt.run_apt_update_command")
    @mock.patch("uaclient.apt.run_apt_command")
    @mock.patch("uaclient.system.should_reboot", return_value=False)
    @mock.patch("uaclient.util.prompt_choices", return_value="a")
    @mock.patch("uaclient.cli.fix.get_cloud_type", return_value=(None, None))
    @mock.patch("builtins.input", return_value="pro_token")
    @mock.patch(M_PATH + "_handle_subscription_for_required_service")
    @mock.patch("uaclient.cli.fix.attach_with_token")
    def test_execute_fix_plan_when_attach_is_needed(
        self,
        m_attach_with_token,
        m_handle_required_service,
        _m_input,
        _m_get_cloud_type,
        _m_prompt,
        _m_should_reboot,
        _m_run_apt_command,
        _m_run_apt_update,
        fix_plan,
        expected_output,
        expected_fix_status,
        expected_unfixed_pkgs,
        FakeConfig,
        capsys,
    ):
        def fake_attach(cfg, token, allow_enable):
            cfg.for_attached_machine()
            return 0

        m_attach_with_token.side_effect = fake_attach
        m_handle_required_service.return_value = True
        with mock.patch("uaclient.util.sys") as m_sys:
            m_stdout = mock.MagicMock()
            type(m_sys).stdout = m_stdout
            type(m_stdout).encoding = mock.PropertyMock(return_value="utf-8")
            assert (
                expected_fix_status,
                expected_unfixed_pkgs,
            ) == execute_fix_plan(fix_plan, dry_run=False, cfg=FakeConfig())

        out, _ = capsys.readouterr()
        assert expected_output in out

    @pytest.mark.parametrize(
        "service_status",
        (
            (UserFacingStatus.INACTIVE),
            (UserFacingStatus.INAPPLICABLE),
            (UserFacingStatus.UNAVAILABLE),
        ),
    )
    @pytest.mark.parametrize(
        "fix_plan,expected_output,expected_fix_status,"
        "expected_unfixed_pkgs",
        (
            (  # installing package fixes that comes from
                # standard-updates and esm-infra when attaching
                # the system
                FixPlanResult(
                    title="USN-###",
                    description="test",
                    expected_status=FixStatus.SYSTEM_NON_VULNERABLE.value.msg,
                    affected_packages=["pkg1"],
                    plan=[
                        FixPlanAttachStep(
                            data=AttachData(
                                reason="test",
                                required_service=ESM_INFRA_POCKET,
                                source_packages=["pkg1"],
                            ),
                            order=1,
                        ),
                        FixPlanEnableStep(
                            data=EnableData(
                                service=ESM_INFRA_POCKET,
                                source_packages=["pkg1"],
                            ),
                            order=2,
                        ),
                        FixPlanAptUpgradeStep(
                            data=AptUpgradeData(
                                binary_packages=["pkg1"],
                                source_packages=["pkg1"],
                                pocket=ESM_INFRA_POCKET,
                            ),
                            order=3,
                        ),
                    ],
                    warnings=[],
                    error=None,
                    additional_data=None,
                ),
                textwrap.dedent(
                    """\
                    1 affected source package is installed: pkg1
                    (1/1) pkg1:
                    A fix is available in Ubuntu Pro: ESM Infra.
                    """
                )
                + messages.SECURITY_UPDATE_NOT_INSTALLED_SUBSCRIPTION
                + "\n"
                + messages.PROMPT_ENTER_TOKEN
                + "\n"
                + colorize_commands([["pro attach pro_token"]])
                + "\n"
                + messages.SECURITY_UA_SERVICE_NOT_ENTITLED.format(
                    service="esm-infra"
                )  # noqa
                + "\n\n"
                + "1 package is still affected: pkg1"
                + "\n"
                + "{check} USN-### is not resolved.\n".format(
                    check=messages.FAIL_X
                ),
                FixStatus.SYSTEM_STILL_VULNERABLE,
                [
                    UnfixedPackage(
                        pkg="pkg1",
                        unfixed_reason=messages.SECURITY_UA_SERVICE_NOT_ENABLED_SHORT.format(  # noqa
                            service="esm-infra"
                        ),
                    ),
                ],
            ),
        ),
    )
    @mock.patch("uaclient.apt.run_apt_update_command")
    @mock.patch("uaclient.apt.run_apt_command")
    @mock.patch("uaclient.system.should_reboot", return_value=False)
    @mock.patch("uaclient.util.prompt_choices", return_value="a")
    @mock.patch(M_PATH + "get_cloud_type", return_value=(None, None))
    @mock.patch("builtins.input", return_value="pro_token")
    @mock.patch(M_PATH + "attach_with_token")
    def test_execute_fix_plan_when_service_is_not_entitled(
        self,
        m_attach_with_token,
        _m_input,
        _m_get_cloud_type,
        _m_prompt,
        _m_should_reboot,
        _m_run_apt_command,
        _m_run_apt_update,
        fix_plan,
        expected_output,
        expected_fix_status,
        expected_unfixed_pkgs,
        service_status,
        FakeConfig,
        capsys,
    ):
        def fake_attach(cfg, token, allow_enable):
            cfg.for_attached_machine()
            return 0

        m_attach_with_token.side_effect = fake_attach

        m_entitlement_cls = mock.MagicMock()
        m_entitlement_obj = m_entitlement_cls.return_value
        m_entitlement_obj.user_facing_status.return_value = (
            service_status,
            "",
        )
        m_entitlement_obj.applicability_status.return_value = (
            ApplicabilityStatus.INAPPLICABLE,
            "",
        )
        m_entitlement_obj.name = "esm-infra"

        with mock.patch(
            "uaclient.cli.fix.entitlement_factory",
            return_value=m_entitlement_cls,
        ):
            with mock.patch("uaclient.util.sys") as m_sys:
                m_stdout = mock.MagicMock()
                type(m_sys).stdout = m_stdout
                type(m_stdout).encoding = mock.PropertyMock(
                    return_value="utf-8"
                )
                assert (
                    expected_fix_status,
                    expected_unfixed_pkgs,
                ) == execute_fix_plan(
                    fix_plan, dry_run=False, cfg=FakeConfig()
                )

        out, _ = capsys.readouterr()
        assert expected_output in out

    @pytest.mark.parametrize(
        "fix_plan,prompt_value,expected_output,"
        "expected_fix_status,expected_unfixed_pkgs",
        (
            (  # installing package fixes that comes from
                # standard-updates and esm-infra when attaching
                # the system
                FixPlanResult(
                    title="USN-###",
                    description="test",
                    expected_status=FixStatus.SYSTEM_NON_VULNERABLE.value.msg,
                    affected_packages=["pkg1"],
                    plan=[
                        FixPlanEnableStep(
                            data=EnableData(
                                service=ESM_INFRA_POCKET,
                                source_packages=["pkg1"],
                            ),
                            order=1,
                        ),
                        FixPlanAptUpgradeStep(
                            data=AptUpgradeData(
                                binary_packages=["pkg1"],
                                source_packages=["pkg1"],
                                pocket=ESM_INFRA_POCKET,
                            ),
                            order=2,
                        ),
                    ],
                    warnings=[],
                    error=None,
                    additional_data=None,
                ),
                "e",
                textwrap.dedent(
                    """\
                    1 affected source package is installed: pkg1
                    (1/1) pkg1:
                    A fix is available in Ubuntu Pro: ESM Infra.
                    """
                )
                + messages.SECURITY_SERVICE_DISABLED.format(
                    service="esm-infra"
                )
                + "\n"
                + colorize_commands([["pro enable esm-infra"]])
                + "\n"
                + colorize_commands(
                    [["apt update && apt install --only-upgrade" " -y pkg1"]]
                )
                + "\n\n"
                + "{check} USN-### is resolved.\n".format(
                    check=messages.OKGREEN_CHECK
                ),
                FixStatus.SYSTEM_NON_VULNERABLE,
                [],
            ),
            (
                FixPlanResult(
                    title="USN-###",
                    description="test",
                    expected_status=FixStatus.SYSTEM_NON_VULNERABLE.value.msg,
                    affected_packages=["pkg1"],
                    plan=[
                        FixPlanEnableStep(
                            data=EnableData(
                                service=ESM_INFRA_POCKET,
                                source_packages=["pkg1"],
                            ),
                            order=1,
                        ),
                        FixPlanAptUpgradeStep(
                            data=AptUpgradeData(
                                binary_packages=["pkg1"],
                                source_packages=["pkg1"],
                                pocket=ESM_INFRA_POCKET,
                            ),
                            order=2,
                        ),
                    ],
                    warnings=[],
                    error=None,
                    additional_data=None,
                ),
                "c",
                textwrap.dedent(
                    """\
                    1 affected source package is installed: pkg1
                    (1/1) pkg1:
                    A fix is available in Ubuntu Pro: ESM Infra.
                    """
                )
                + messages.SECURITY_SERVICE_DISABLED.format(
                    service="esm-infra"
                )
                + "\n"
                + messages.SECURITY_UA_SERVICE_NOT_ENABLED.format(
                    service="esm-infra"
                )
                + "\n\n"
                + "1 package is still affected: pkg1"
                + "\n"
                + "{check} USN-### is not resolved.\n".format(
                    check=messages.FAIL_X
                ),
                FixStatus.SYSTEM_STILL_VULNERABLE,
                [
                    UnfixedPackage(
                        pkg="pkg1",
                        unfixed_reason=messages.SECURITY_UA_SERVICE_NOT_ENABLED_SHORT.format(  # noqa
                            service="esm-infra"
                        ),
                    )
                ],
            ),
        ),
    )
    @mock.patch("uaclient.apt.run_apt_update_command")
    @mock.patch("uaclient.apt.run_apt_command")
    @mock.patch(M_PATH + "enable_entitlement_by_name")
    @mock.patch("uaclient.system.should_reboot", return_value=False)
    @mock.patch("uaclient.util.prompt_choices")
    @mock.patch(M_PATH + "get_cloud_type", return_value=(None, None))
    @mock.patch("builtins.input", return_value="pro_token")
    def test_execute_fix_plan_when_service_requires_enable(
        self,
        _m_input,
        _m_get_cloud_type,
        m_prompt,
        _m_should_reboot,
        m_enable_ent,
        _m_run_apt_command,
        _m_run_apt_update,
        fix_plan,
        prompt_value,
        expected_output,
        expected_fix_status,
        expected_unfixed_pkgs,
        FakeConfig,
        capsys,
    ):
        cfg = FakeConfig().for_attached_machine
        m_enable_ent.return_value = (True, None)
        m_prompt.return_value = prompt_value

        m_entitlement_cls = mock.MagicMock()
        m_entitlement_obj = m_entitlement_cls.return_value
        m_entitlement_obj.user_facing_status.return_value = (
            UserFacingStatus.INACTIVE,
            "",
        )
        m_entitlement_obj.applicability_status.return_value = (
            ApplicabilityStatus.APPLICABLE,
            "",
        )
        m_entitlement_obj.name = "esm-infra"

        with mock.patch(
            "uaclient.cli.fix.entitlement_factory",
            return_value=m_entitlement_cls,
        ):
            with mock.patch("uaclient.util.sys") as m_sys:
                m_stdout = mock.MagicMock()
                type(m_sys).stdout = m_stdout
                type(m_stdout).encoding = mock.PropertyMock(
                    return_value="utf-8"
                )
                out, _ = capsys.readouterr()
                assert (
                    expected_fix_status,
                    expected_unfixed_pkgs,
                ) == execute_fix_plan(fix_plan, dry_run=False, cfg=cfg)

        out, _ = capsys.readouterr()
        assert expected_output in out

    @pytest.mark.parametrize(
        "fix_plan,prompt_value,expected_output,"
        "expected_fix_status,expected_unfixed_pkgs",
        (
            (
                FixPlanResult(
                    title="USN-###",
                    description="test",
                    expected_status=FixStatus.SYSTEM_NON_VULNERABLE.value.msg,
                    affected_packages=["pkg1"],
                    plan=[
                        FixPlanAttachStep(
                            data=AttachData(
                                reason="test",
                                required_service=ESM_INFRA_POCKET,
                                source_packages=["pkg1"],
                            ),
                            order=1,
                        ),
                        FixPlanEnableStep(
                            data=EnableData(
                                service=ESM_INFRA_POCKET,
                                source_packages=["pkg1"],
                            ),
                            order=2,
                        ),
                        FixPlanAptUpgradeStep(
                            data=AptUpgradeData(
                                binary_packages=["pkg1"],
                                source_packages=["pkg1"],
                                pocket=ESM_INFRA_POCKET,
                            ),
                            order=3,
                        ),
                    ],
                    warnings=[],
                    error=None,
                    additional_data=None,
                ),
                "r",
                textwrap.dedent(
                    """\
                    1 affected source package is installed: pkg1
                    (1/1) pkg1:
                    A fix is available in Ubuntu Pro: ESM Infra.
                    """
                )
                + messages.SECURITY_UPDATE_NOT_INSTALLED_EXPIRED
                + "\n"
                + messages.PROMPT_EXPIRED_ENTER_TOKEN
                + "\n"
                + colorize_commands([["pro detach"]])
                + "\n"
                + colorize_commands([["pro attach pro_token"]])
                + "\n"
                + colorize_commands(
                    [["apt update && apt install --only-upgrade" " -y pkg1"]]
                )
                + "\n\n"
                + "{check} USN-### is resolved.\n".format(
                    check=messages.OKGREEN_CHECK
                ),
                FixStatus.SYSTEM_NON_VULNERABLE,
                [],
            ),
            (
                FixPlanResult(
                    title="USN-###",
                    description="test",
                    expected_status=FixStatus.SYSTEM_NON_VULNERABLE.value.msg,
                    affected_packages=["pkg1"],
                    plan=[
                        FixPlanAttachStep(
                            data=AttachData(
                                reason="test",
                                required_service=ESM_INFRA_POCKET,
                                source_packages=["pkg1"],
                            ),
                            order=1,
                        ),
                        FixPlanEnableStep(
                            data=EnableData(
                                service=ESM_INFRA_POCKET,
                                source_packages=["pkg1"],
                            ),
                            order=2,
                        ),
                        FixPlanAptUpgradeStep(
                            data=AptUpgradeData(
                                binary_packages=["pkg1"],
                                source_packages=["pkg1"],
                                pocket=ESM_INFRA_POCKET,
                            ),
                            order=3,
                        ),
                    ],
                    warnings=[],
                    error=None,
                    additional_data=None,
                ),
                "c",
                textwrap.dedent(
                    """\
                    1 affected source package is installed: pkg1
                    (1/1) pkg1:
                    A fix is available in Ubuntu Pro: ESM Infra.
                    """
                )
                + messages.SECURITY_UPDATE_NOT_INSTALLED_EXPIRED
                + "\n\n"
                + "1 package is still affected: pkg1"
                + "\n"
                + "{check} USN-### is not resolved.\n".format(
                    check=messages.FAIL_X
                ),
                FixStatus.SYSTEM_STILL_VULNERABLE,
                [
                    UnfixedPackage(
                        pkg="pkg1",
                        unfixed_reason=messages.SECURITY_UA_SERVICE_WITH_EXPIRED_SUB.format(  # noqa
                            service="esm-infra"
                        ),
                    )
                ],
            ),
        ),
    )
    @mock.patch("uaclient.cli.action_detach")
    @mock.patch(M_PATH + "attach_with_token")
    @mock.patch(M_PATH + "_check_subscription_is_expired")
    @mock.patch(M_PATH + "_handle_subscription_for_required_service")
    @mock.patch("uaclient.apt.run_apt_update_command")
    @mock.patch("uaclient.apt.run_apt_command")
    @mock.patch("uaclient.system.should_reboot", return_value=False)
    @mock.patch("uaclient.util.prompt_choices")
    @mock.patch(M_PATH + "get_cloud_type", return_value=(None, None))
    @mock.patch("builtins.input", return_value="pro_token")
    def test_execute_fix_plan_when_subscription_is_expired(
        self,
        _m_input,
        _m_get_cloud_type,
        m_prompt,
        _m_should_reboot,
        _m_run_apt_command,
        _m_run_apt_update,
        m_handle_required_service,
        m_check_subscription_expired,
        m_attach_with_token,
        _m_action_detach,
        fix_plan,
        prompt_value,
        expected_output,
        expected_fix_status,
        expected_unfixed_pkgs,
        FakeConfig,
        capsys,
    ):
        cfg = FakeConfig().for_attached_machine()
        m_handle_required_service.return_value = True
        m_check_subscription_expired.return_value = True
        m_prompt.return_value = prompt_value

        with mock.patch("uaclient.util.sys") as m_sys:
            m_stdout = mock.MagicMock()
            type(m_sys).stdout = m_stdout
            type(m_stdout).encoding = mock.PropertyMock(return_value="utf-8")
            out, _ = capsys.readouterr()
            assert (
                expected_fix_status,
                expected_unfixed_pkgs,
            ) == execute_fix_plan(fix_plan, dry_run=False, cfg=cfg)

        out, _ = capsys.readouterr()
        assert expected_output in out

    @pytest.mark.parametrize(
        "fix_plan,check_notices,cloud_type,expected_output,"
        "expected_fix_status,expected_unfixed_pkgs",
        (
            (  # No affected_packages listed, but reboot required
                FixPlanResult(
                    title="USN-###",
                    description="test",
                    expected_status=FixStatus.SYSTEM_NOT_AFFECTED.value.msg,
                    affected_packages=[],
                    plan=[
                        FixPlanNoOpStep(
                            data=NoOpData(
                                status=FixPlanNoOpStatus.NOT_AFFECTED.value
                            ),
                            order=1,
                        )
                    ],
                    warnings=[],
                    error=None,
                    additional_data=None,
                ),
                False,
                (None, None),
                textwrap.dedent(
                    """\
                   No affected source packages are installed.

                   {check} USN-### does not affect your system.
                   """.format(
                        check=messages.OKGREEN_CHECK  # noqa: E126
                    )  # noqa: E126
                ),
                FixStatus.SYSTEM_NOT_AFFECTED,
                [],
            ),
            (  # installing package fix and reboot required
                FixPlanResult(
                    title="USN-###",
                    description="test",
                    expected_status=FixStatus.SYSTEM_NON_VULNERABLE.value.msg,
                    affected_packages=["pkg1"],
                    plan=[
                        FixPlanAptUpgradeStep(
                            data=AptUpgradeData(
                                binary_packages=["pkg1"],
                                source_packages=["pkg1"],
                                pocket=STANDARD_UPDATES_POCKET,
                            ),
                            order=1,
                        )
                    ],
                    warnings=[],
                    error=None,
                    additional_data=None,
                ),
                True,
                (None, None),
                textwrap.dedent(
                    """\
                   1 affected source package is installed: pkg1
                   (1/1) pkg1:
                   A fix is available in Ubuntu standard updates.
                   """
                )
                + colorize_commands(
                    [["apt update && apt install --only-upgrade" " -y pkg1"]]
                )
                + "\n\n"
                + "A reboot is required to complete fix operation."
                + "\n"
                + "{check} USN-### is not resolved.\n".format(
                    check=messages.FAIL_X
                ),
                FixStatus.SYSTEM_VULNERABLE_UNTIL_REBOOT,
                [],
            ),
        ),
    )
    @mock.patch("uaclient.files.notices.NoticesManager.add")
    @mock.patch("uaclient.system.should_reboot", return_value=True)
    @mock.patch("uaclient.cli.fix.get_cloud_type")
    @mock.patch("uaclient.apt.run_apt_update_command")
    @mock.patch("uaclient.apt.run_apt_command")
    def test_execute_fix_plan_when_reboot_required_needed(
        self,
        _m_apt_run_cmd,
        _m_apt_run_update,
        m_get_cloud_type,
        _m_should_reboot,
        m_add_notice,
        fix_plan,
        check_notices,
        cloud_type,
        expected_output,
        expected_fix_status,
        expected_unfixed_pkgs,
        capsys,
        FakeConfig,
    ):
        m_get_cloud_type.return_value = cloud_type
        with mock.patch("uaclient.util.sys") as m_sys:
            m_stdout = mock.MagicMock()
            type(m_sys).stdout = m_stdout
            type(m_stdout).encoding = mock.PropertyMock(return_value="utf-8")
            assert (
                expected_fix_status,
                expected_unfixed_pkgs,
            ) == execute_fix_plan(fix_plan, dry_run=False, cfg=FakeConfig())

        out, _ = capsys.readouterr()
        assert expected_output in out

        if check_notices:
            assert [
                mock.call(
                    Notice.ENABLE_REBOOT_REQUIRED,
                    messages.ENABLE_REBOOT_REQUIRED_TMPL.format(
                        operation="fix operation"
                    ),
                )
            ] == m_add_notice.call_args_list


class TestExecuteAptUpgradeStep:
    @mock.patch("uaclient.util.we_are_currently_root", return_value=False)
    def test_execute_apt_upgrade_step_return_early_if_non_root(
        self,
        _m_we_are_root,
        capsys,
    ):
        step = FixPlanAptUpgradeStep(
            data=AptUpgradeData(
                binary_packages=["pkg1"],
                source_packages=["pkg1"],
                pocket=STANDARD_UPDATES_POCKET,
            ),
            order=1,
        )
        context = FixContext(
            title="test",
            dry_run=False,
            affected_pkgs=[],
            cfg=None,
        )

        with mock.patch("uaclient.util.sys") as m_sys:
            m_stdout = mock.MagicMock()
            type(m_sys).stdout = m_stdout
            type(m_stdout).encoding = mock.PropertyMock(return_value="utf-8")
            _execute_apt_upgrade_step(context, step)

        out, _ = capsys.readouterr()
        assert messages.SECURITY_APT_NON_ROOT in out


class TestExecuteAttachStep:
    def test_execute_attach_step_print_message_succeed_on_dry_run(
        self, capsys, FakeConfig
    ):
        step = FixPlanAttachStep(
            data=AttachData(
                reason="test",
                required_service=ESM_INFRA_POCKET,
                source_packages=["slsrc"],
            ),
            order=1,
        )
        context = FixContext(
            title="test",
            dry_run=True,
            affected_pkgs=[],
            cfg=FakeConfig(),
        )

        with mock.patch("uaclient.util.sys") as m_sys:
            m_stdout = mock.MagicMock()
            type(m_sys).stdout = m_stdout
            type(m_stdout).encoding = mock.PropertyMock(return_value="utf-8")
            _execute_attach_step(context, step)

        out, _ = capsys.readouterr()
        assert messages.SECURITY_DRY_RUN_UA_NOT_ATTACHED in out
        assert context.fix_status == FixStatus.SYSTEM_NON_VULNERABLE


class TestExecuteEnableStep:
    def test_execute_enable_step_check_service_on_dry_run(
        self, capsys, FakeConfig
    ):
        step = FixPlanEnableStep(
            data=EnableData(
                service=ESM_INFRA_POCKET,
                source_packages=["slsrc"],
            ),
            order=1,
        )
        context = FixContext(
            title="test",
            dry_run=True,
            affected_pkgs=[],
            cfg=FakeConfig(),
        )

        m_entitlement_cls = mock.MagicMock()
        m_entitlement_obj = m_entitlement_cls.return_value
        m_entitlement_obj.user_facing_status.return_value = (
            UserFacingStatus.INACTIVE,
            "",
        )
        m_entitlement_obj.applicability_status.return_value = (
            ApplicabilityStatus.APPLICABLE,
            "",
        )
        m_entitlement_obj.name = "esm-infra"

        with mock.patch("uaclient.util.sys") as m_sys:
            m_stdout = mock.MagicMock()
            type(m_sys).stdout = m_stdout
            type(m_stdout).encoding = mock.PropertyMock(return_value="utf-8")
            with mock.patch(
                "uaclient.cli.fix.entitlement_factory",
                return_value=m_entitlement_cls,
            ):
                _execute_enable_step(context, step)

        out, _ = capsys.readouterr()
        assert (
            messages.SECURITY_DRY_RUN_UA_SERVICE_NOT_ENABLED.format(
                service="esm-infra"
            )
            in out
        )
        assert context.fix_status == FixStatus.SYSTEM_NON_VULNERABLE


class TestHandleSubscriptionForRequiredService:
    @pytest.mark.parametrize(
        "dry_run",
        ((True), (False)),
    )
    def test_handle_subscription_when_service_enabled(self, dry_run, capsys):
        m_entitlement_cls = mock.MagicMock()
        m_entitlement_obj = m_entitlement_cls.return_value
        m_entitlement_obj.user_facing_status.return_value = (
            UserFacingStatus.ACTIVE,
            "",
        )
        m_entitlement_obj.name = "esm-infra"

        with mock.patch("uaclient.util.sys") as m_sys:
            m_stdout = mock.MagicMock()
            type(m_sys).stdout = m_stdout
            type(m_stdout).encoding = mock.PropertyMock(return_value="utf-8")
            with mock.patch(
                "uaclient.cli.fix.entitlement_factory",
                return_value=m_entitlement_cls,
            ):
                assert _handle_subscription_for_required_service(
                    service="esm-infra",
                    cfg=None,
                    dry_run=dry_run,
                )
        out, _ = capsys.readouterr()
        assert "" == out


class TestPerformMagicAttach:
    @mock.patch(M_PATH + "_initiate")
    @mock.patch(M_PATH + "_wait")
    @mock.patch(M_PATH + "_revoke")
    def test_magic_attach_revoke_token_if_wait_fails(
        self,
        m_initiate,
        m_wait,
        m_revoke,
    ):
        m_initiate.return_value = mock.MagicMock(
            token="token", user_code="user_code"
        )
        m_wait.side_effect = exceptions.MagicAttachTokenError()

        with pytest.raises(exceptions.MagicAttachTokenError):
            _perform_magic_attach(cfg=None)

        assert 1 == m_initiate.call_count
        assert 1 == m_wait.call_count
        assert 1 == m_revoke.call_count


class TestFixUSN:
    @mock.patch("uaclient.apt.run_apt_update_command")
    @mock.patch("uaclient.apt.run_apt_command")
    @mock.patch(M_PATH + "_prompt_for_attach", return_value=False)
    @mock.patch(M_PATH + "usn_plan")
    def test_fix_usn_with_related_usns(
        self,
        m_usn_plan,
        _m_prompt_for_attach,
        _m_run_apt_command,
        _m_run_apt_update,
        capsys,
        FakeConfig,
    ):
        fix_plan = USNSFixPlanResult(
            usns_data=USNFixPlanResult(
                expected_status=FixStatus.SYSTEM_NON_VULNERABLE,
                usns=[
                    FixPlanUSNResult(
                        target_usn_plan=FixPlanResult(
                            title="USN-1235-1",
                            description="test",
                            expected_status=FixStatus.SYSTEM_NON_VULNERABLE.value.msg,  # noqa
                            affected_packages=["pkg1"],
                            plan=[
                                FixPlanAptUpgradeStep(
                                    data=AptUpgradeData(
                                        binary_packages=["pkg1"],
                                        source_packages=["pkg1"],
                                        pocket=STANDARD_UPDATES_POCKET,
                                    ),
                                    order=1,
                                )
                            ],
                            warnings=[],
                            error=None,
                            additional_data=USNAdditionalData(
                                associated_cves=[],
                                associated_launchpad_bugs=[],
                            ),
                        ),
                        related_usns_plan=[
                            FixPlanResult(
                                title="USN-4561-1",
                                description="test",
                                expected_status=FixStatus.SYSTEM_NON_VULNERABLE.value.msg,  # noqa
                                affected_packages=["pkg2"],
                                plan=[
                                    FixPlanAttachStep(
                                        data=AttachData(
                                            reason="test",
                                            required_service="esm-infra",
                                            source_packages=["pkg2"],
                                        ),
                                        order=1,
                                    ),
                                    FixPlanEnableStep(
                                        data=EnableData(
                                            service="esm-infra",
                                            source_packages=["pkg2"],
                                        ),
                                        order=2,
                                    ),
                                    FixPlanAptUpgradeStep(
                                        data=AptUpgradeData(
                                            binary_packages=["pkg2"],
                                            source_packages=["pkg2"],
                                            pocket=ESM_INFRA_POCKET,
                                        ),
                                        order=3,
                                    ),
                                ],
                                warnings=[],
                                error=None,
                                additional_data=USNAdditionalData(
                                    associated_cves=[],
                                    associated_launchpad_bugs=[],
                                ),
                            ),
                            FixPlanResult(
                                title="USN-7891-1",
                                description="test",
                                expected_status=FixStatus.SYSTEM_NON_VULNERABLE.value.msg,  # noqa
                                affected_packages=["pkg3", "pkg4"],
                                plan=[
                                    FixPlanAttachStep(
                                        data=AttachData(
                                            reason="test",
                                            required_service=ESM_APPS_POCKET,
                                            source_packages=["pkg3", "pkg4"],
                                        ),
                                        order=1,
                                    ),
                                    FixPlanEnableStep(
                                        data=EnableData(
                                            service="esm-apps",
                                            source_packages=["pkg3", "pkg4"],
                                        ),
                                        order=2,
                                    ),
                                    FixPlanAptUpgradeStep(
                                        data=AptUpgradeData(
                                            binary_packages=["pkg3", "pkg4"],
                                            source_packages=["pkg3", "pkg4"],
                                            pocket=ESM_APPS_POCKET,
                                        ),
                                        order=3,
                                    ),
                                ],
                                warnings=[],
                                error=None,
                                additional_data=USNAdditionalData(
                                    associated_cves=[],
                                    associated_launchpad_bugs=[],
                                ),
                            ),
                            FixPlanResult(
                                title="USN-8221-1",
                                description="test",
                                expected_status=FixStatus.SYSTEM_NON_VULNERABLE.value.msg,  # noqa
                                affected_packages=["pkg5"],
                                plan=[],
                                warnings=[
                                    FixPlanWarningSecurityIssueNotFixed(
                                        data=SecurityIssueNotFixedData(
                                            source_packages=["pkg5"],
                                            status="pending",
                                        ),
                                        order=1,
                                    ),
                                ],
                                error=None,
                                additional_data=USNAdditionalData(
                                    associated_cves=[],
                                    associated_launchpad_bugs=[],
                                ),
                            ),
                        ],
                    )
                ],
            )
        )
        m_usn_plan.return_value = fix_plan
        issue_id = "USN-1231-1"

        with mock.patch("uaclient.util.sys") as m_sys:
            m_stdout = mock.MagicMock()
            type(m_sys).stdout = m_stdout
            type(m_stdout).encoding = mock.PropertyMock(return_value="utf-8")
            actual_ret = fix_usn(
                security_issue=issue_id,
                dry_run=False,
                no_related=False,
                cfg=FakeConfig(),
            )

        expected_msg = (
            "\n"
            + messages.SECURITY_FIXING_REQUESTED_USN.format(issue_id=issue_id)
            + "\n"
            + textwrap.dedent(
                """\
                1 affected source package is installed: pkg1
                (1/1) pkg1:
                A fix is available in Ubuntu standard updates.
                """
            )
            + colorize_commands(
                [["apt update && apt install --only-upgrade" " -y pkg1"]]
            )
            + "\n\n"
            + "{check} USN-1235-1 is resolved.\n".format(
                check=messages.OKGREEN_CHECK
            )
            + "\n"
            + textwrap.dedent(
                """\
                Found related USNs:
                - USN-4561-1
                - USN-7891-1
                - USN-8221-1
                """
            )
            + "\n"
            + textwrap.dedent(
                """\
                Fixing related USNs:
                - USN-4561-1
                1 affected source package is installed: pkg2
                (1/1) pkg2:
                A fix is available in Ubuntu Pro: ESM Infra.
                """
            )
            + "\n"
            + "1 package is still affected: pkg2"
            + "\n"
            + "{check} USN-4561-1 is not resolved.".format(
                check=messages.FAIL_X
            )
            + "\n\n"
            + textwrap.dedent(
                """\
                - USN-7891-1
                2 affected source packages are installed: pkg3, pkg4
                (1/2, 2/2) pkg3, pkg4:
                A fix is available in Ubuntu Pro: ESM Apps.
                """
            )
            + "\n"
            + "2 packages are still affected: pkg3, pkg4"
            + "\n"
            + "{check} USN-7891-1 is not resolved.".format(
                check=messages.FAIL_X
            )
            + "\n\n"
            + textwrap.dedent(
                """\
                - USN-8221-1
                1 affected source package is installed: pkg5
                (1/1) pkg5:
                A fix is coming soon. Try again tomorrow.
                """
            )
            + "\n"
            + "1 package is still affected: pkg5"
            + "\n"
            + "{check} USN-8221-1 is not resolved.".format(
                check=messages.FAIL_X
            )
            + "\n\n"
            + "Summary:"
            + "\n"
            + "{check} USN-1231-1 [requested] is resolved.".format(
                check=messages.OKGREEN_CHECK
            )
            + "\n"
            + "{check} USN-4561-1 [related] is not resolved.".format(
                check=messages.FAIL_X
            )
            + "\n"
            + "  - pkg2: esm-infra is required for upgrade."
            + "\n"
            + "{check} USN-7891-1 [related] is not resolved.".format(
                check=messages.FAIL_X
            )
            + "\n"
            + "  - pkg3: esm-apps is required for upgrade."
            + "\n"
            + "  - pkg4: esm-apps is required for upgrade."
            + "\n"
            + "{check} USN-8221-1 [related] is not resolved.".format(
                check=messages.FAIL_X
            )
            + "\n"
            + "  - pkg5: A fix is coming soon. Try again tomorrow."
            + "\n\n"
            + messages.SECURITY_RELATED_USN_ERROR.format(issue_id="USN-1231-1")
        )
        out, _ = capsys.readouterr()
        assert expected_msg in out
        assert FixStatus.SYSTEM_NON_VULNERABLE == actual_ret

    @mock.patch("uaclient.apt.run_apt_update_command")
    @mock.patch("uaclient.apt.run_apt_command")
    @mock.patch(M_PATH + "usn_plan")
    def test_fix_usn_when_no_related_value_is_true(
        self,
        m_usn_plan,
        _m_run_apt_command,
        _m_run_apt_update,
        capsys,
        FakeConfig,
    ):
        issue_id = "USN-1235-1"
        fix_plan = USNSFixPlanResult(
            usns_data=USNFixPlanResult(
                expected_status=FixStatus.SYSTEM_NON_VULNERABLE,
                usns=[
                    FixPlanUSNResult(
                        target_usn_plan=FixPlanResult(
                            title=issue_id,
                            description="test",
                            expected_status=FixStatus.SYSTEM_NON_VULNERABLE.value.msg,  # noqa
                            affected_packages=["pkg1"],
                            plan=[
                                FixPlanAptUpgradeStep(
                                    data=AptUpgradeData(
                                        binary_packages=["pkg1"],
                                        source_packages=["pkg1"],
                                        pocket=STANDARD_UPDATES_POCKET,
                                    ),
                                    order=1,
                                )
                            ],
                            warnings=[],
                            error=None,
                            additional_data=USNAdditionalData(
                                associated_cves=[],
                                associated_launchpad_bugs=[],
                            ),
                        ),
                        related_usns_plan=[
                            FixPlanResult(
                                title="USN-4561-1",
                                description="test",
                                expected_status=FixStatus.SYSTEM_NON_VULNERABLE.value.msg,  # noqa
                                affected_packages=["pkg2"],
                                plan=[
                                    FixPlanAttachStep(
                                        data=AttachData(
                                            reason="test",
                                            required_service="esm-infra",
                                            source_packages=["pkg2"],
                                        ),
                                        order=1,
                                    ),
                                    FixPlanEnableStep(
                                        data=EnableData(
                                            service="esm-infra",
                                            source_packages=["pkg2"],
                                        ),
                                        order=2,
                                    ),
                                    FixPlanAptUpgradeStep(
                                        data=AptUpgradeData(
                                            binary_packages=["pkg2"],
                                            source_packages=["pkg2"],
                                            pocket=ESM_INFRA_POCKET,
                                        ),
                                        order=3,
                                    ),
                                ],
                                warnings=[],
                                error=None,
                                additional_data=USNAdditionalData(
                                    associated_cves=[],
                                    associated_launchpad_bugs=[],
                                ),
                            ),
                            FixPlanResult(
                                title="USN-7891-1",
                                description="test",
                                expected_status=FixStatus.SYSTEM_NON_VULNERABLE.value.msg,  # noqa
                                affected_packages=["pkg3", "pkg4"],
                                plan=[
                                    FixPlanAttachStep(
                                        data=AttachData(
                                            reason="test",
                                            required_service=ESM_APPS_POCKET,
                                            source_packages=["pkg3", "pkg4"],
                                        ),
                                        order=1,
                                    ),
                                    FixPlanEnableStep(
                                        data=EnableData(
                                            service="esm-apps",
                                            source_packages=["pkg3", "pkg4"],
                                        ),
                                        order=2,
                                    ),
                                    FixPlanAptUpgradeStep(
                                        data=AptUpgradeData(
                                            binary_packages=["pkg3", "pkg4"],
                                            source_packages=["pkg3", "pkg4"],
                                            pocket=ESM_APPS_POCKET,
                                        ),
                                        order=3,
                                    ),
                                ],
                                warnings=[],
                                error=None,
                                additional_data=USNAdditionalData(
                                    associated_cves=[],
                                    associated_launchpad_bugs=[],
                                ),
                            ),
                        ],
                    )
                ],
            )
        )
        m_usn_plan.return_value = fix_plan

        with mock.patch("uaclient.util.sys") as m_sys:
            m_stdout = mock.MagicMock()
            type(m_sys).stdout = m_stdout
            type(m_stdout).encoding = mock.PropertyMock(return_value="utf-8")
            actual_ret = fix_usn(
                security_issue=issue_id,
                dry_run=False,
                no_related=True,
                cfg=FakeConfig(),
            )

        expected_msg = (
            "USN-1235-1: test"
            + "\n\n"
            + messages.SECURITY_FIXING_REQUESTED_USN.format(issue_id=issue_id)
            + "\n"
            + textwrap.dedent(
                """\
                1 affected source package is installed: pkg1
                (1/1) pkg1:
                A fix is available in Ubuntu standard updates.
                """
            )
            + colorize_commands(
                [["apt update && apt install --only-upgrade" " -y pkg1"]]
            )
            + "\n\n"
            + "{check} USN-1235-1 is resolved.\n".format(
                check=messages.OKGREEN_CHECK
            )
        )

        out, _ = capsys.readouterr()
        assert expected_msg == out
        assert FixStatus.SYSTEM_NON_VULNERABLE == actual_ret
