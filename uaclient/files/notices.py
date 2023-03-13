import logging
import os
from collections import namedtuple
from enum import Enum
from typing import List

from uaclient import defaults, event_logger, messages, system, util

LOG = logging.getLogger(__name__)
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
        notice_details: Notice,
        description: str,
    ):
        """Adds a notice file. If the notice is found,
        it overwrites it.

        :param notice_details: Holds details concerning the notice file.
        :param description: The content to be written to the notice file.
        """
        if not util.we_are_currently_root():
            with util.disable_log_to_console():
                LOG.warning("Trying to add a notice as non-root user")
            return

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

    def remove(self, notice_details: Notice):
        """Deletes a notice file.

        :param notice_details: Holds details concerning the notice file.
        """
        if not util.we_are_currently_root():
            with util.disable_log_to_console():
                LOG.warning("Trying to remove a notice as non-root user")
            return

        directory = (
            defaults.NOTICES_PERMANENT_DIRECTORY
            if notice_details.value.is_permanent
            else defaults.NOTICES_TEMPORARY_DIRECTORY
        )
        filename = "{}-{}".format(
            notice_details.value.order_id, notice_details.value.label
        )
        system.ensure_file_absent(os.path.join(directory, filename))

    def list(self) -> List[str]:
        """Gets all the notice files currently saved.

        :returns: List of notice file contents.
        """
        notice_directories = (
            defaults.NOTICES_PERMANENT_DIRECTORY,
            defaults.NOTICES_TEMPORARY_DIRECTORY,
        )
        notices = []
        for notice_directory in notice_directories:
            if not os.path.exists(notice_directory):
                continue
            notice_file_names = [
                file_name
                for file_name in os.listdir(notice_directory)
                if os.path.isfile(os.path.join(notice_directory, file_name))
            ]
            for notice_file_name in notice_file_names:
                notice_file_contents = system.load_file(
                    os.path.join(notice_directory, notice_file_name)
                )
                if notice_file_contents:
                    notices.append(notice_file_contents)
                else:
                    # if no contents of file, default to message
                    # defined in the enum
                    try:
                        order_id, label = notice_file_name.split("-")
                        notice = None
                        for n in Notice:
                            if n.order_id == order_id and n.label == label:
                                notice = n
                        if notice is None:
                            raise Exception()
                        notices.append(notice.value.message)
                    except Exception:
                        with util.disable_log_to_console():
                            logging.warning(
                                "Something went wrong while processing"
                                " notice: {}.".format(
                                    notice_file_name,
                                )
                            )
        notices.sort()
        return notices


_notice_cls = None


def get_notice():
    global _notice_cls
    if _notice_cls is None:
        _notice_cls = NoticesManager()

    return _notice_cls


def add(notice_details: Notice, **kwargs) -> None:
    notice = get_notice()
    description = notice_details.message.format(**kwargs)
    notice.add(notice_details, description)


def remove(notice_details: Notice) -> None:
    notice = get_notice()
    notice.remove(notice_details)


def list() -> List[str]:
    notice = get_notice()
    return notice.list()
