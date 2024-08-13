import os

import mock
import pytest

from uaclient import defaults
from uaclient.conftest import FakeNotice
from uaclient.files import notices
from uaclient.files.notices import NoticesManager


class TestNotices:
    @pytest.mark.parametrize(
        "label,content",
        (
            (
                FakeNotice.reboot_script_failed,
                "notice_a2",
            ),
        ),
    )
    @mock.patch("uaclient.files.notices.system.write_file")
    def test_add(
        self,
        sys_write_file,
        label,
        content,
    ):
        notice = NoticesManager()
        notice.add(label, content)
        assert [
            mock.call(
                os.path.join(
                    defaults.NOTICES_PERMANENT_DIRECTORY,
                    "12-reboot_script_failed",
                ),
                content,
            )
        ] == sys_write_file.call_args_list

    @mock.patch("uaclient.util.we_are_currently_root", return_value=False)
    @mock.patch("uaclient.files.notices.system.write_file")
    def test_add_non_root(
        self,
        m_sys_write_file,
        m_we_are_currently_root,
        caplog_text,
    ):
        notice = NoticesManager()
        notice.add(FakeNotice.reboot_required, "content")
        assert [] == m_sys_write_file.call_args_list
        assert (
            "NoticesManager.add(reboot_required) called as non-root user"
            in caplog_text()
        )

    @pytest.mark.parametrize(
        "label,content",
        (
            (
                FakeNotice.reboot_required,
                "notice_a",
            ),
        ),
    )
    def test_add_duplicate_label(
        self,
        label,
        content,
    ):
        notice = NoticesManager()
        notice.add(label, content)
        with mock.patch(
            "uaclient.files.notices.system.write_file"
        ) as sys_write_file:
            notice.add(label, content)
            assert 1 == sys_write_file.call_count

    @pytest.mark.parametrize(
        "label,content",
        (
            (
                FakeNotice.reboot_script_failed,
                "notice_a2",
            ),
        ),
    )
    @mock.patch("uaclient.files.notices.system.ensure_file_absent")
    def test_remove(
        self,
        sys_file_absent,
        label,
        content,
    ):
        notice = NoticesManager()
        notice.add(label, content)
        notice.remove(label)
        assert [
            mock.call(
                os.path.join(
                    defaults.NOTICES_PERMANENT_DIRECTORY,
                    "12-reboot_script_failed",
                ),
            )
        ] == sys_file_absent.call_args_list

    @mock.patch("uaclient.util.we_are_currently_root", return_value=False)
    @mock.patch("uaclient.files.notices.system.ensure_file_absent")
    def test_remove_non_root(
        self,
        m_sys_file_absent,
        m_we_are_currently_root,
        caplog_text,
    ):
        notice = NoticesManager()
        notice.remove(FakeNotice.reboot_required)
        assert [] == m_sys_file_absent.call_args_list
        assert (
            "NoticesManager.remove(reboot_required) called as non-root user"
            in caplog_text()
        )

    @mock.patch("uaclient.files.notices.NoticesManager.list")
    @mock.patch("uaclient.files.notices.NoticesManager.remove")
    @mock.patch("uaclient.files.notices.NoticesManager.add")
    def test_notice_module(
        self, notice_cls_add, notice_cls_remove, notice_cls_read
    ):
        notices.add(FakeNotice.reboot_required)
        assert [
            mock.call(FakeNotice.reboot_required, "notice_a"),
        ] == notice_cls_add.call_args_list
        notices.remove(FakeNotice.reboot_required)
        assert [
            mock.call(FakeNotice.reboot_required)
        ] == notice_cls_remove.call_args_list
        notices.list()
        assert 1 == notice_cls_read.call_count

    @mock.patch("uaclient.files.notices.NoticesManager._get_notice_file_names")
    def test_get_notice_file_names(self, m_get_notice_file_names):
        notice = NoticesManager()
        m_get_notice_file_names.return_value = []
        assert [] == notice._get_notice_file_names("directory")
        m_get_notice_file_names.return_value = ["file1", "file2", "file3"]
        assert ["file1", "file2", "file3"] == notice._get_notice_file_names(
            "directory"
        )

    @mock.patch("uaclient.files.notices.NoticesManager._get_notice_file_names")
    @mock.patch("uaclient.system.load_file")
    def test_list(self, m_load_file, m_get_notice_file_names):
        notice = NoticesManager()

        m_get_notice_file_names.side_effect = lambda directory: (
            []
            if directory == defaults.NOTICES_TEMPORARY_DIRECTORY
            else ["1-fakeNotice"]
        )
        m_load_file.return_value = "test"

        assert ["test"] == notice.list()
