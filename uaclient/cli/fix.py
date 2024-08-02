import re
import textwrap
from typing import (  # noqa: F401
    Dict,
    List,
    NamedTuple,
    Optional,
    Set,
    Tuple,
    Union,
)

from uaclient import apt, exceptions, messages, system, util
from uaclient.actions import attach_with_token, enable_entitlement_by_name
from uaclient.api.u.pro.attach.magic.initiate.v1 import _initiate
from uaclient.api.u.pro.attach.magic.revoke.v1 import (
    MagicAttachRevokeOptions,
    _revoke,
)
from uaclient.api.u.pro.attach.magic.wait.v1 import (
    MagicAttachWaitOptions,
    _wait,
)
from uaclient.api.u.pro.security.fix._common import (
    CVE_OR_USN_REGEX,
    FixStatus,
    UnfixedPackage,
    status_message,
)
from uaclient.api.u.pro.security.fix._common.plan.v1 import (  # noqa: F401
    ESM_APPS_POCKET,
    ESM_INFRA_POCKET,
    STANDARD_UPDATES_POCKET,
    FixPlanAptUpgradeStep,
    FixPlanAttachStep,
    FixPlanEnableStep,
    FixPlanNoOpAlreadyFixedStep,
    FixPlanNoOpLivepatchFixStep,
    FixPlanNoOpStatus,
    FixPlanNoOpStep,
    FixPlanResult,
    FixPlanStep,
    FixPlanUSNResult,
    FixPlanWarning,
    FixPlanWarningFailUpdatingESMCache,
    FixPlanWarningPackageCannotBeInstalled,
    FixPlanWarningSecurityIssueNotFixed,
    NoOpAlreadyFixedData,
    NoOpLivepatchFixData,
    USNAdditionalData,
)
from uaclient.api.u.pro.security.fix.cve.plan.v1 import CVEFixPlanOptions
from uaclient.api.u.pro.security.fix.cve.plan.v1 import _plan as cve_plan
from uaclient.api.u.pro.security.fix.usn.plan.v1 import USNFixPlanOptions
from uaclient.api.u.pro.security.fix.usn.plan.v1 import _plan as usn_plan
from uaclient.api.u.pro.status.is_attached.v1 import (
    ContractExpiryStatus,
    _is_attached,
)
from uaclient.cli.commands import ProArgument, ProArgumentGroup, ProCommand
from uaclient.cli.detach import action_detach
from uaclient.cli.parser import HelpCategory
from uaclient.clouds.identity import (
    CLOUD_TYPE_TO_TITLE,
    PRO_CLOUD_URLS,
    get_cloud_type,
)
from uaclient.config import UAConfig
from uaclient.defaults import PRINT_WRAP_WIDTH
from uaclient.entitlements import entitlement_factory
from uaclient.entitlements.entitlement_status import (
    ApplicabilityStatus,
    CanEnableFailure,
    UserFacingStatus,
)
from uaclient.files import notices
from uaclient.files.notices import Notice
from uaclient.messages.urls import PRO_HOME_PAGE
from uaclient.status import colorize_commands


class FixContext:
    def __init__(
        self,
        title: str,
        dry_run: bool,
        affected_pkgs: List[str],
        cfg: UAConfig,
    ):
        self.pkg_index = 0
        self.unfixed_pkgs = []  # type: List[UnfixedPackage]
        self.installed_pkgs = set()  # type: Set[str]
        self.fix_status = FixStatus.SYSTEM_NON_VULNERABLE
        self.title = title
        self.affected_pkgs = affected_pkgs
        self.dry_run = dry_run
        self.cfg = cfg
        self.should_print_pkg_header = True
        self.warn_package_cannot_be_installed = False
        self.fixed_by_livepatch = False

    def print_fix_header(self):
        if self.affected_pkgs:
            msg = messages.SECURITY_AFFECTED_PKGS.pluralize(
                len(self.affected_pkgs)
            ).format(
                count=len(self.affected_pkgs),
                pkgs=", ".join(sorted(self.affected_pkgs)),
            )
            print(
                textwrap.fill(
                    msg,
                    width=PRINT_WRAP_WIDTH,
                    subsequent_indent="    ",
                    replace_whitespace=False,
                )
            )

    def print_pkg_header(
        self,
        source_pkgs: List[str],
        status: str,
        pocket: Optional[str] = None,
    ):
        if self.should_print_pkg_header:
            print(
                _format_packages_message(
                    pkg_list=source_pkgs,
                    status=status,
                    pkg_index=self.pkg_index,
                    num_pkgs=len(self.affected_pkgs),
                    pocket_source=(
                        get_pocket_description(pocket) if pocket else None
                    ),
                )
            )

    def add_unfixed_packages(self, pkgs: List[str], unfixed_reason: str):
        for pkg in pkgs:
            self.unfixed_pkgs.append(
                UnfixedPackage(pkg=pkg, unfixed_reason=unfixed_reason)
            )


def print_cve_header(cve: FixPlanResult):
    lines = [
        "{issue}: {description}".format(
            issue=cve.title.upper(), description=cve.description
        ),
        " - https://ubuntu.com/security/{}".format(cve.title.upper()),
    ]

    print("\n".join(lines))


def print_usn_header(fix_plan: FixPlanUSNResult):
    target_usn = fix_plan.target_usn_plan
    lines = [
        "{issue}: {description}".format(
            issue=target_usn.title.upper(), description=target_usn.description
        ),
    ]

    additional_data = target_usn.additional_data
    if isinstance(additional_data, USNAdditionalData):
        if additional_data.associated_cves:
            lines.append(messages.SECURITY_FOUND_CVES)
            for cve in additional_data.associated_cves:
                lines.append(
                    " - {}".format(
                        messages.urls.SECURITY_CVE_PAGE.format(cve=cve)
                    )
                )
        elif additional_data.associated_launchpad_bugs:
            lines.append(messages.SECURITY_FOUND_LAUNCHPAD_BUGS)
            for lp_bug in additional_data.associated_launchpad_bugs:
                lines.append(" - " + lp_bug)

    print("\n".join(lines))


def fix_cve(security_issue: str, dry_run: bool, cfg: UAConfig):
    fix_plan = cve_plan(
        options=CVEFixPlanOptions(cves=[security_issue]), cfg=cfg
    )

    error = fix_plan.cves_data.cves[0].error
    if error and error.msg:
        raise exceptions.AnonymousUbuntuProError(
            named_msg=messages.NamedMessage(
                error.code or "unexpected-error", error.msg
            )
        )
    print_cve_header(fix_plan.cves_data.cves[0])
    print()

    status, _ = execute_fix_plan(fix_plan.cves_data.cves[0], dry_run, cfg)
    return status


def fix_usn(
    security_issue: str, dry_run: bool, no_related: bool, cfg: UAConfig
):
    fix_plan = usn_plan(
        options=USNFixPlanOptions(usns=[security_issue]), cfg=cfg
    )
    error = fix_plan.usns_data.usns[0].target_usn_plan.error
    if error and error.msg:
        raise exceptions.AnonymousUbuntuProError(
            named_msg=messages.NamedMessage(
                error.code or "unexpected-error", error.msg
            )
        )
    print_usn_header(fix_plan.usns_data.usns[0])

    print(
        "\n"
        + messages.SECURITY_FIXING_REQUESTED_USN.format(
            issue_id=security_issue
        )
    )

    target_usn_status, _ = execute_fix_plan(
        fix_plan.usns_data.usns[0].target_usn_plan,
        dry_run,
        cfg,
    )

    if target_usn_status not in (
        FixStatus.SYSTEM_NON_VULNERABLE,
        FixStatus.SYSTEM_NOT_AFFECTED,
    ):
        return target_usn_status

    related_usns_plan = fix_plan.usns_data.usns[0].related_usns_plan
    if not related_usns_plan or no_related:
        return target_usn_status

    print(
        "\n"
        + messages.SECURITY_RELATED_USNS.format(
            related_usns="\n- ".join(usn.title for usn in related_usns_plan)
        )
    )

    print("\n" + messages.SECURITY_FIXING_RELATED_USNS)
    related_usn_status = (
        {}
    )  # type: Dict[str, Tuple[FixStatus, List[UnfixedPackage]]]
    for related_usn_plan in related_usns_plan:
        print("- {}".format(related_usn_plan.title))
        related_usn_status[related_usn_plan.title] = execute_fix_plan(
            related_usn_plan,
            dry_run,
            cfg,
        )
        print()

    print(messages.SECURITY_USN_SUMMARY)
    _handle_fix_status_message(
        target_usn_status,
        security_issue,
        context=messages.FIX_ISSUE_CONTEXT_REQUESTED,
    )

    failure_on_related_usn = False
    for related_usn_plan in related_usns_plan:
        status, unfixed_pkgs = related_usn_status[related_usn_plan.title]
        _handle_fix_status_message(
            status,
            related_usn_plan.title,
            context=messages.FIX_ISSUE_CONTEXT_RELATED,
        )

        if status == FixStatus.SYSTEM_VULNERABLE_UNTIL_REBOOT:
            print(
                "- "
                + messages.ENABLE_REBOOT_REQUIRED_TMPL.format(
                    operation="fix operation"
                )
            )
            failure_on_related_usn = True
        if status == FixStatus.SYSTEM_STILL_VULNERABLE:
            for unfixed_pkg in unfixed_pkgs:
                if unfixed_pkg.unfixed_reason:
                    print(
                        "  - {}: {}".format(
                            unfixed_pkg.pkg, unfixed_pkg.unfixed_reason
                        )
                    )
            failure_on_related_usn = True

    if failure_on_related_usn:
        print(
            "\n"
            + messages.SECURITY_RELATED_USN_ERROR.format(
                issue_id=security_issue
            )
        )

    return target_usn_status


def _format_packages_message(
    pkg_list: List[str],
    status: str,
    pkg_index: int,
    num_pkgs: int,
    pocket_source: Optional[str] = None,
) -> str:
    """Format the packages and status to an user friendly message."""
    if not pkg_list:
        return ""

    msg_index = []
    src_pkgs = []
    for src_pkg in pkg_list:
        pkg_index += 1
        msg_index.append("{}/{}".format(pkg_index, num_pkgs))
        src_pkgs.append(src_pkg)

    msg_header = textwrap.fill(
        "{} {}:".format(
            "(" + ", ".join(msg_index) + ")", ", ".join(sorted(src_pkgs))
        ),
        width=PRINT_WRAP_WIDTH,
        subsequent_indent="    ",
    )
    return "{}\n{}".format(msg_header, status_message(status, pocket_source))


def _run_ua_attach(cfg: UAConfig, token: str) -> bool:
    """Attach to an Ubuntu Pro subscription with a given token.

    :return: True if attach performed without errors.
    """
    print(colorize_commands([["pro", "attach", token]]))
    try:
        attach_with_token(cfg, token=token, allow_enable=True)
        return True
    except exceptions.UbuntuProError as err:
        print(err.msg)
        return False


def _inform_ubuntu_pro_existence_if_applicable() -> None:
    """Alert the user when running Pro on cloud with PRO support."""
    cloud_type, _ = get_cloud_type()
    if cloud_type in PRO_CLOUD_URLS.keys():
        print(
            messages.SECURITY_USE_PRO_TMPL.format(
                title=CLOUD_TYPE_TO_TITLE.get(cloud_type),
                cloud_specific_url=PRO_CLOUD_URLS.get(cloud_type),
            )
        )


def _perform_magic_attach(cfg: UAConfig):
    print(messages.CLI_MAGIC_ATTACH_INIT)
    initiate_resp = _initiate(cfg=cfg)
    print(
        "\n"
        + messages.CLI_MAGIC_ATTACH_SIGN_IN.format(
            user_code=initiate_resp.user_code
        )
    )

    wait_options = MagicAttachWaitOptions(magic_token=initiate_resp.token)

    try:
        wait_resp = _wait(options=wait_options, cfg=cfg)
    except exceptions.MagicAttachTokenError as e:
        print(messages.CLI_MAGIC_ATTACH_FAILED)

        revoke_options = MagicAttachRevokeOptions(
            magic_token=initiate_resp.token
        )
        _revoke(options=revoke_options, cfg=cfg)
        raise e

    print("\n" + messages.CLI_MAGIC_ATTACH_PROCESSING)
    return _run_ua_attach(cfg, wait_resp.contract_token)


def _prompt_for_attach(cfg: UAConfig) -> bool:
    """Prompt for attach to a subscription or token.

    :return: True if attach performed.
    """
    _inform_ubuntu_pro_existence_if_applicable()
    print(messages.SECURITY_UPDATE_NOT_INSTALLED_SUBSCRIPTION)
    choice = util.prompt_choices(
        messages.SECURITY_FIX_ATTACH_PROMPT,
        valid_choices=["s", "a", "c"],
    )
    if choice == "c":
        return False
    if choice == "s":
        return _perform_magic_attach(cfg)
    if choice == "a":
        print(messages.PROMPT_ENTER_TOKEN)
        token = input("> ")
        return _run_ua_attach(cfg, token)

    return True


def _format_unfixed_packages_msg(unfixed_pkgs: List[str]) -> str:
    """Format the list of unfixed packages into an message.

    :returns: A string containing the message output for the unfixed
              packages.
    """
    num_pkgs_unfixed = len(unfixed_pkgs)
    return textwrap.fill(
        messages.SECURITY_PKG_STILL_AFFECTED.pluralize(
            num_pkgs_unfixed
        ).format(
            num_pkgs=num_pkgs_unfixed,
            pkgs=", ".join(sorted(unfixed_pkgs)),
        ),
        width=PRINT_WRAP_WIDTH,
        subsequent_indent="    ",
    )


def _check_subscription_is_expired(cfg: UAConfig, dry_run: bool) -> bool:
    """Check if the Ubuntu Pro subscription is expired.

    :returns: True if subscription is expired and not renewed.
    """
    contract_expiry_status = _is_attached(cfg).contract_status
    if (
        contract_expiry_status
        and contract_expiry_status == ContractExpiryStatus.EXPIRED.value
    ):
        if dry_run:
            print(messages.SECURITY_DRY_RUN_UA_EXPIRED_SUBSCRIPTION)
            return False
        return True

    return False


def _prompt_for_new_token(cfg: UAConfig) -> bool:
    """Prompt for attach a new subscription token to the user.

    :return: True if attach performed.
    """
    import argparse

    _inform_ubuntu_pro_existence_if_applicable()
    print(messages.SECURITY_UPDATE_NOT_INSTALLED_EXPIRED)
    choice = util.prompt_choices(
        messages.SECURITY_FIX_RENEW_PROMPT.format(url=PRO_HOME_PAGE),
        valid_choices=["r", "c"],
    )
    if choice == "r":
        print(messages.PROMPT_EXPIRED_ENTER_TOKEN)
        token = input("> ")
        print(colorize_commands([["pro", "detach"]]))
        action_detach(argparse.Namespace(assume_yes=True, format="cli"), cfg)
        return _run_ua_attach(cfg, token)

    return False


def _prompt_for_enable(cfg: UAConfig, service: str) -> bool:
    """Prompt for enable a pro service.

    :return: True if enable performed.
    """
    print(messages.SECURITY_SERVICE_DISABLED.format(service=service))
    choice = util.prompt_choices(
        messages.SECURITY_FIX_ENABLE_PROMPT.format(service=service),
        valid_choices=["e", "c"],
    )

    if choice == "e":
        print(colorize_commands([["pro", "enable", service]]))
        ret, reason = enable_entitlement_by_name(cfg=cfg, name=service)

        if (
            not ret
            and reason is not None
            and isinstance(reason, CanEnableFailure)
        ):
            if reason.message is not None:
                print(reason.message.msg)

        return ret

    return False


def _handle_subscription_for_required_service(
    service: str, cfg: UAConfig, dry_run: bool
) -> bool:
    """
    Verify if the Ubuntu Pro subscription has the required service enabled.
    """
    ent = entitlement_factory(cfg=cfg, name=service)
    if ent:
        ent_status, _ = ent.user_facing_status()

        if ent_status == UserFacingStatus.ACTIVE:
            return True

        applicability_status, _ = ent.applicability_status()
        if applicability_status == ApplicabilityStatus.APPLICABLE:
            if dry_run:
                print(
                    "\n"
                    + messages.SECURITY_DRY_RUN_UA_SERVICE_NOT_ENABLED.format(
                        service=ent.name
                    )
                )
                return True

            if _prompt_for_enable(cfg, ent.name):
                return True
            else:
                print(
                    messages.SECURITY_UA_SERVICE_NOT_ENABLED.format(
                        service=ent.name
                    )
                )

        else:
            print(
                messages.SECURITY_UA_SERVICE_NOT_ENTITLED.format(
                    service=ent.name
                )
            )

    return False


def _handle_fix_status_message(
    status: FixStatus, issue_id: str, context: str = ""
):
    if status == FixStatus.SYSTEM_NON_VULNERABLE:
        if context:
            msg = messages.SECURITY_ISSUE_RESOLVED_ISSUE_CONTEXT.format(
                issue=issue_id, context=context
            )
        else:
            msg = messages.SECURITY_ISSUE_RESOLVED.format(issue=issue_id)
        print(util.handle_unicode_characters(msg))
    elif status == FixStatus.SYSTEM_NOT_AFFECTED:
        if context:
            msg = messages.SECURITY_ISSUE_UNAFFECTED_ISSUE_CONTEXT.format(
                issue=issue_id, context=context
            )
        else:
            msg = messages.SECURITY_ISSUE_UNAFFECTED.format(issue=issue_id)
        print(util.handle_unicode_characters(msg))
    elif status == FixStatus.SYSTEM_VULNERABLE_UNTIL_REBOOT:
        if context:
            msg = messages.SECURITY_ISSUE_NOT_RESOLVED_ISSUE_CONTEXT.format(
                issue=issue_id, context=context
            )
        else:
            msg = messages.SECURITY_ISSUE_NOT_RESOLVED.format(issue=issue_id)
        print(util.handle_unicode_characters(msg))
    else:
        if context:
            msg = messages.SECURITY_ISSUE_NOT_RESOLVED_ISSUE_CONTEXT.format(
                issue=issue_id, context=context
            )
        else:
            msg = messages.SECURITY_ISSUE_NOT_RESOLVED.format(issue=issue_id)
        print(util.handle_unicode_characters(msg))


def get_pocket_description(pocket: str):
    if pocket == STANDARD_UPDATES_POCKET:
        return messages.SECURITY_UBUNTU_STANDARD_UPDATES_POCKET
    elif pocket == ESM_INFRA_POCKET:
        return messages.SECURITY_UA_INFRA_POCKET
    elif pocket == ESM_APPS_POCKET:
        return messages.SECURITY_UA_APPS_POCKET
    else:
        return pocket


def _execute_package_cannot_be_installed_step(
    fix_context: FixContext,
    step: FixPlanWarningPackageCannotBeInstalled,
):
    fix_context.print_pkg_header(
        source_pkgs=step.data.related_source_packages,
        status="released",
        pocket=step.data.pocket,
    )
    fix_context.should_print_pkg_header = False

    warn_msg = messages.FIX_CANNOT_INSTALL_PACKAGE.format(
        package=step.data.binary_package,
        version=step.data.binary_package_version,
    )
    print("- " + warn_msg)

    fix_context.add_unfixed_packages(
        pkgs=[step.data.source_package], unfixed_reason=warn_msg
    )

    fix_context.warn_package_cannot_be_installed = True
    fix_context.fix_status = FixStatus.SYSTEM_STILL_VULNERABLE


def _execute_security_issue_not_fixed_step(
    fix_context: FixContext, step: FixPlanWarningSecurityIssueNotFixed
):
    fix_context.print_pkg_header(
        source_pkgs=step.data.source_packages,
        status=step.data.status,
    )
    fix_context.pkg_index += len(step.data.source_packages)

    fix_context.add_unfixed_packages(
        pkgs=step.data.source_packages,
        unfixed_reason=status_message(step.data.status),
    )
    fix_context.fix_status = FixStatus.SYSTEM_STILL_VULNERABLE


def _execute_fail_updating_esm_cache_step(
    fix_context: FixContext, step: FixPlanWarningFailUpdatingESMCache
):
    if util.we_are_currently_root():
        print(messages.CLI_FIX_FAIL_UPDATING_ESM_CACHE)
    else:
        print("\n" + messages.CLI_FIX_FAIL_UPDATING_ESM_CACHE_NON_ROOT + "\n")


def _execute_apt_upgrade_step(
    fix_context: FixContext,
    step: FixPlanAptUpgradeStep,
):
    fix_context.print_pkg_header(
        source_pkgs=step.data.source_packages,
        status="released",
        pocket=step.data.pocket,
    )
    fix_context.pkg_index += len(step.data.source_packages)

    if not step.data.binary_packages:
        if not fix_context.warn_package_cannot_be_installed:
            print(messages.SECURITY_UPDATE_INSTALLED)
        fix_context.fix_status = FixStatus.SYSTEM_NON_VULNERABLE
        return

    if not util.we_are_currently_root() and not fix_context.dry_run:
        print(messages.SECURITY_APT_NON_ROOT)
        fix_context.fix_status = FixStatus.SYSTEM_STILL_VULNERABLE
        fix_context.add_unfixed_packages(
            pkgs=step.data.source_packages,
            unfixed_reason=messages.SECURITY_APT_NON_ROOT,
        )
        return

    print(
        colorize_commands(
            [
                ["apt", "update", "&&"]
                + ["apt", "install", "--only-upgrade", "-y"]
                + sorted(step.data.binary_packages)
            ]
        )
    )

    if fix_context.dry_run:
        fix_context.fix_status = FixStatus.SYSTEM_NON_VULNERABLE
        return

    try:
        apt.run_apt_update_command()
        apt.run_apt_command(
            cmd=["apt-get", "install", "--only-upgrade", "-y"]
            + step.data.binary_packages,
            override_env_vars={"DEBIAN_FRONTEND": "noninteractive"},
        )
    except Exception as e:
        msg = getattr(e, "msg", str(e))
        print(msg)
        fix_context.fix_status = FixStatus.SYSTEM_STILL_VULNERABLE
        fix_context.add_unfixed_packages(
            pkgs=step.data.source_packages,
            unfixed_reason=msg,
        )
        return

    fix_context.fix_status = FixStatus.SYSTEM_NON_VULNERABLE
    fix_context.should_print_pkg_header = True
    fix_context.installed_pkgs.update(step.data.binary_packages)


def _execute_attach_step(
    fix_context: FixContext,
    step: FixPlanAttachStep,
):
    pocket = (
        ESM_INFRA_POCKET
        if step.data.required_service == "esm-infra"
        else ESM_APPS_POCKET
    )
    fix_context.print_pkg_header(
        source_pkgs=step.data.source_packages,
        status="released",
        pocket=pocket,
    )

    fix_context.should_print_pkg_header = False
    if not _is_attached(fix_context.cfg).is_attached:
        if fix_context.dry_run:
            print("\n" + messages.SECURITY_DRY_RUN_UA_NOT_ATTACHED)
        else:
            if not _prompt_for_attach(fix_context.cfg):
                fix_context.fix_status = FixStatus.SYSTEM_STILL_VULNERABLE
                fix_context.add_unfixed_packages(
                    pkgs=step.data.source_packages,
                    unfixed_reason=messages.SECURITY_UA_SERVICE_REQUIRED.format(  # noqa
                        service=step.data.required_service
                    ),
                )
                return
    elif _check_subscription_is_expired(
        cfg=fix_context.cfg, dry_run=fix_context.dry_run
    ):
        if fix_context.dry_run:
            print(messages.SECURITY_DRY_RUN_UA_EXPIRED_SUBSCRIPTION)
        elif not _prompt_for_new_token(fix_context.cfg):
            fix_context.fix_status = FixStatus.SYSTEM_STILL_VULNERABLE
            fix_context.add_unfixed_packages(
                pkgs=step.data.source_packages,
                unfixed_reason=messages.SECURITY_UA_SERVICE_WITH_EXPIRED_SUB.format(  # noqa
                    service=step.data.required_service
                ),
            )
            return

    fix_context.fix_status = FixStatus.SYSTEM_NON_VULNERABLE


def _execute_enable_step(
    fix_context: FixContext,
    step: FixPlanEnableStep,
):
    pocket = (
        ESM_INFRA_POCKET
        if step.data.service == "esm-infra"
        else ESM_APPS_POCKET
    )
    fix_context.print_pkg_header(
        source_pkgs=step.data.source_packages,
        status="released",
        pocket=pocket,
    )
    fix_context.should_print_pkg_header = False

    if not _handle_subscription_for_required_service(  # noqa
        step.data.service,
        fix_context.cfg,
        fix_context.dry_run,
    ):
        fix_context.add_unfixed_packages(
            pkgs=step.data.source_packages,
            unfixed_reason=messages.SECURITY_UA_SERVICE_NOT_ENABLED_SHORT.format(  # noqa
                service=step.data.service
            ),
        )
        fix_context.fix_status = FixStatus.SYSTEM_STILL_VULNERABLE
        return

    return FixStatus.SYSTEM_NON_VULNERABLE


def _execute_noop_not_affected_step(
    fix_context: FixContext, step: FixPlanNoOpStep
):
    if step.data.status == FixPlanNoOpStatus.NOT_AFFECTED.value:
        print(messages.SECURITY_NO_AFFECTED_PKGS)
        fix_context.fix_status = FixStatus.SYSTEM_NOT_AFFECTED


def _execute_noop_fixed_by_livepatch_step(
    fix_context: FixContext, step: FixPlanNoOpLivepatchFixStep
):
    if isinstance(step.data, NoOpLivepatchFixData):
        print(
            messages.CVE_FIXED_BY_LIVEPATCH.format(
                issue=fix_context.title,
                version=step.data.patch_version,
            )
        )
        fix_context.fixed_by_livepatch = True


def _execute_noop_already_fixed_step(
    fix_context: FixContext, step: FixPlanNoOpAlreadyFixedStep
):
    if isinstance(step.data, NoOpAlreadyFixedData):
        fix_context.print_pkg_header(
            source_pkgs=step.data.source_packages,
            status="released",
            pocket=step.data.pocket,
        )
        print(messages.SECURITY_UPDATE_INSTALLED)
        fix_context.pkg_index += len(step.data.source_packages)


def execute_fix_plan(
    fix_plan: FixPlanResult, dry_run: bool, cfg: UAConfig
) -> Tuple[FixStatus, List[UnfixedPackage]]:
    full_plan = [
        *fix_plan.plan,
        *fix_plan.warnings,
    ]  # type: List[Union[FixPlanStep, FixPlanWarning]]

    fix_context = FixContext(
        title=fix_plan.title,
        dry_run=dry_run,
        affected_pkgs=fix_plan.affected_packages or [],
        cfg=cfg,
    )
    fix_context.print_fix_header()

    for step in sorted(full_plan, key=lambda x: x.order):
        if isinstance(step, FixPlanWarningPackageCannotBeInstalled):
            _execute_package_cannot_be_installed_step(fix_context, step)
        if isinstance(step, FixPlanWarningSecurityIssueNotFixed):
            _execute_security_issue_not_fixed_step(fix_context, step)
        if isinstance(step, FixPlanWarningFailUpdatingESMCache):
            _execute_fail_updating_esm_cache_step(fix_context, step)
        if isinstance(step, FixPlanAptUpgradeStep):
            _execute_apt_upgrade_step(fix_context, step)

            if fix_context.fix_status != FixStatus.SYSTEM_NON_VULNERABLE:
                break
        if isinstance(step, FixPlanAttachStep):
            _execute_attach_step(fix_context, step)

            if fix_context.fix_status != FixStatus.SYSTEM_NON_VULNERABLE:
                break
        if isinstance(step, FixPlanEnableStep):
            _execute_enable_step(fix_context, step)

            if fix_context.fix_status != FixStatus.SYSTEM_NON_VULNERABLE:
                break

        if isinstance(step, FixPlanNoOpStep):
            _execute_noop_not_affected_step(fix_context, step)
        if isinstance(step, FixPlanNoOpLivepatchFixStep):
            _execute_noop_fixed_by_livepatch_step(fix_context, step)
        if isinstance(step, FixPlanNoOpAlreadyFixedStep):
            _execute_noop_already_fixed_step(fix_context, step)

    print()
    if fix_context.unfixed_pkgs:
        print(
            _format_unfixed_packages_msg(
                list(
                    set(
                        [
                            unfixed_pkg.pkg
                            for unfixed_pkg in fix_context.unfixed_pkgs
                        ]
                    )
                )
            )
        )
        fix_context.fix_status = FixStatus.SYSTEM_STILL_VULNERABLE

    if (
        fix_context.fix_status == FixStatus.SYSTEM_NON_VULNERABLE
        and system.should_reboot(installed_pkgs=fix_context.installed_pkgs)
    ):
        fix_context.fix_status = FixStatus.SYSTEM_VULNERABLE_UNTIL_REBOOT
        reboot_msg = messages.ENABLE_REBOOT_REQUIRED_TMPL.format(
            operation="fix operation"
        )
        print(reboot_msg)
        notices.add(
            Notice.ENABLE_REBOOT_REQUIRED,
            operation="fix operation",
        )

    if not fix_context.fixed_by_livepatch:
        _handle_fix_status_message(fix_context.fix_status, fix_plan.title)

    return (fix_context.fix_status, fix_context.unfixed_pkgs)


def action_fix(args, *, cfg, **kwargs):
    if not re.match(CVE_OR_USN_REGEX, args.security_issue):
        raise exceptions.InvalidSecurityIssueIdFormat(
            issue=args.security_issue
        )

    if args.dry_run:
        print(messages.SECURITY_DRY_RUN_WARNING)

    if "cve" in args.security_issue.lower():
        status = fix_cve(args.security_issue, args.dry_run, cfg)
    else:
        status = fix_usn(
            args.security_issue, args.dry_run, args.no_related, cfg
        )

    return status.exit_code


fix_command = ProCommand(
    "fix",
    help=messages.CLI_ROOT_FIX,
    description=messages.CLI_FIX_DESC,
    action=action_fix,
    help_category=HelpCategory.SECURITY,
    argument_groups=[
        ProArgumentGroup(
            arguments=[
                ProArgument("security_issue", help=messages.CLI_FIX_ISSUE),
                ProArgument(
                    "--dry-run",
                    help=messages.CLI_FIX_DRY_RUN,
                    action="store_true",
                ),
                ProArgument(
                    "--no-related",
                    help=messages.CLI_FIX_NO_RELATED,
                    action="store_true",
                ),
            ]
        )
    ],
)
