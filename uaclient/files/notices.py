import os
from collections import namedtuple
from enum import Enum
from typing import List, Tuple

from uaclient import defaults, event_logger, messages, system

event = event_logger.get_event_logger()
NoticeFileDetails = namedtuple(
    "NoticeFileDetails", ["order_id", "label", "is_permanent", "message"]
)


class Notice(NoticeFileDetails, Enum):
    REBOOT_REQUIRED = NoticeFileDetails(
        label="reboot_required",
        order_id="10",
        is_permanent=False,
        message="System reboot required",
    )
    ENABLE_REBOOT_REQUIRED = NoticeFileDetails(
        label="enable_reboot_required",
        order_id="11",
        is_permanent=False,
        message=messages.ENABLE_REBOOT_REQUIRED_TMPL,
    )
    REBOOT_SCRIPT_FAILED = NoticeFileDetails(
        label="reboot_script_failed",
        order_id="12",
        is_permanent=True,
        message=messages.REBOOT_SCRIPT_FAILED,
    )
    FIPS_REBOOT_REQUIRED = NoticeFileDetails(
        label="fips_reboot_required",
        order_id="20",
        is_permanent=False,
        message=messages.FIPS_REBOOT_REQUIRED_MSG,
    )
    FIPS_SYSTEM_REBOOT_REQUIRED = NoticeFileDetails(
        label="fips_system_reboot_required",
        order_id="21",
        is_permanent=False,
        message=messages.FIPS_SYSTEM_REBOOT_REQUIRED.msg,
    )
    FIPS_INSTALL_OUT_OF_DATE = NoticeFileDetails(
        label="fips_install_out_of_date",
        order_id="22",
        is_permanent=True,
        message=messages.FIPS_INSTALL_OUT_OF_DATE,
    )
    FIPS_DISABLE_REBOOT_REQUIRED = NoticeFileDetails(
        label="fips_disable_reboot_required",
        order_id="23",
        is_permanent=False,
        message=messages.FIPS_DISABLE_REBOOT_REQUIRED,
    )
    FIPS_PROC_FILE_ERROR = NoticeFileDetails(
        label="fips_proc_file_error",
        order_id="24",
        is_permanent=True,
        message=messages.FIPS_PROC_FILE_ERROR,
    )
    FIPS_MANUAL_DISABLE_URL = NoticeFileDetails(
        label="fips_manual_disable_url",
        order_id="25",
        is_permanent=True,
        message=messages.NOTICE_FIPS_MANUAL_DISABLE_URL,
    )
    WRONG_FIPS_METAPACKAGE_ON_CLOUD = NoticeFileDetails(
        label="wrong_fips_metapackage_on_cloud",
        order_id="25",
        is_permanent=True,
        message=messages.NOTICE_WRONG_FIPS_METAPACKAGE_ON_CLOUD,
    )
    LIVEPATCH_LTS_REBOOT_REQUIRED = NoticeFileDetails(
        label="lp_lts_reboot_required",
        order_id="30",
        is_permanent=False,
        message=messages.LIVEPATCH_LTS_REBOOT_REQUIRED,
    )
    CONTRACT_REFRESH_WARNING = NoticeFileDetails(
        label="contract_refresh_warning",
        order_id="40",
        is_permanent=True,
        message=messages.NOTICE_REFRESH_CONTRACT_WARNING,
    )
    OPERATION_IN_PROGRESS = NoticeFileDetails(
        label="operation_in_progress",
        order_id="60",
        is_permanent=False,
        message="Operation in progress: {operation}",
    )
    AUTO_ATTACH_RETRY_FULL_NOTICE = NoticeFileDetails(
        label="auto_attach_retry_full_notice",
        order_id="70",
        is_permanent=False,
        message=messages.AUTO_ATTACH_RETRY_NOTICE,
    )
    AUTO_ATTACH_RETRY_TOTAL_FAILURE = NoticeFileDetails(
        label="auto_attach_total_failure",
        order_id="71",
        is_permanent=True,
        message=messages.AUTO_ATTACH_RETRY_TOTAL_FAILURE_NOTICE,
    )


class NoticesManager:
    def add(
        self,
        root_mode: bool,
        notice_details: Notice,
        description: str,
    ):
        """Adds a notice file. If the notice is found,
        it overwrites it.

        :param notice_details: Holds details concerning the notice file.
        :param description: The content to be written to the notice file.
        """
        if root_mode:
            directory = (
                defaults.NOTICES_PERMANENT_DIRECTORY
                if notice_details.value.is_permanent
                else defaults.NOTICES_TEMPORARY_DIRECTORY
            )
            filename = "{}-{}".format(
                notice_details.value.order_id, notice_details.value.label
            )
            system.write_file(
                os.path.join(directory, filename),
                description,
            )
        else:
            event.warning("Trying to add a notice as non-root user")

    def remove(self, root_mode: bool, notice_details: Notice):
        """Deletes a notice file.

        :param notice_details: Holds details concerning the notice file.
        """
        if root_mode:
            directory = (
                defaults.NOTICES_PERMANENT_DIRECTORY
                if notice_details.value.is_permanent
                else defaults.NOTICES_TEMPORARY_DIRECTORY
            )
            filename = "{}-{}".format(
                notice_details.value.order_id, notice_details.value.label
            )
            system.remove_file(os.path.join(directory, filename))
        else:
            event.warning("Trying to remove a notice as non-root user")

    def list(self) -> List[Tuple[str, str]]:
        """Gets all the notice files currently saved.

        :returns: List of notice file contents.
        """
        notice_directories = (
            defaults.NOTICES_PERMANENT_DIRECTORY,
            defaults.NOTICES_TEMPORARY_DIRECTORY,
        )
        file_notices = []
        for notice_directory in notice_directories:
            if not os.path.exists(notice_directory):
                continue
            notices = [
                file
                for file in os.listdir(notice_directory)
                if os.path.isfile(os.path.join(notice_directory, file))
            ]
            notices = notices if notices is not None else []
            for notice in notices:
                file_notices.append(
                    (
                        "",
                        system.load_file(
                            os.path.join(notice_directory, notice)
                        ),
                    ),
                )
        file_notices.sort()
        return file_notices


_notice_cls = None


def get_notice():
    global _notice_cls
    if _notice_cls is None:
        _notice_cls = NoticesManager()

    return _notice_cls


def add(root_mode: bool, notice_details: Notice, **kwargs) -> None:
    notice = get_notice()
    description = notice_details.message.format(**kwargs)
    notice.add(root_mode, notice_details, description)


def remove(root_mode: bool, notice_details: Notice) -> None:
    notice = get_notice()
    notice.remove(root_mode, notice_details)


def list() -> List[Tuple[str, str]]:
    notice = get_notice()
    return notice.list()
