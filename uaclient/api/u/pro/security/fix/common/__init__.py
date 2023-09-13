from typing import Optional

from uaclient import messages
from uaclient.security import FixStatus


def status_message(status, pocket_source: Optional[str] = None):
    if status == "needed":
        return messages.SECURITY_CVE_STATUS_NEEDED
    elif status == "needs-triage":
        return messages.SECURITY_CVE_STATUS_TRIAGE
    elif status == "pending":
        return messages.SECURITY_CVE_STATUS_PENDING
    elif status in ("ignored", "deferred"):
        return messages.SECURITY_CVE_STATUS_IGNORED
    elif status == "DNE":
        return messages.SECURITY_CVE_STATUS_DNE
    elif status == "not-affected":
        return messages.SECURITY_CVE_STATUS_NOT_AFFECTED
    elif status == "released" and pocket_source:
        return messages.SECURITY_FIX_RELEASE_STREAM.format(
            fix_stream=pocket_source
        )
    return messages.SECURITY_CVE_STATUS_UNKNOWN.format(status=status)


def get_expected_overall_status(
    current_fix_status: str, fix_status: str
) -> str:
    if not current_fix_status:
        return fix_status

    if fix_status in (
        FixStatus.SYSTEM_NON_VULNERABLE.value.msg,
        FixStatus.SYSTEM_NOT_AFFECTED.value.msg,
    ):
        if (
            current_fix_status == FixStatus.SYSTEM_NOT_AFFECTED.value.msg
            and current_fix_status != fix_status
        ):
            return fix_status
        else:
            return current_fix_status
    else:
        # This means the system is still affected and we must
        # priotize this as the global state
        return fix_status
