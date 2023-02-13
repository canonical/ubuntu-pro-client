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
                FakeNotice.a,
                "notice_a",
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
        notice.add(True, label, content)
        assert [
            mock.call(
                os.path.join(defaults.NOTICES_PERMANENT_DIRECTORY, "01-a"),
                content,
            )
        ] == sys_write_file.call_args_list

    @mock.patch("uaclient.files.notices.system.write_file")
    def test_add_non_root(
        self,
        m_sys_write_file,
        caplog_text,
    ):
        notice = NoticesManager()
        notice.add(False, FakeNotice.a, "content")
        assert [] == m_sys_write_file.call_args_list
        assert "Trying to add a notice as non-root user" in caplog_text()

    @pytest.mark.parametrize(
        "label,content",
        (
            (
                FakeNotice.a,
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
        notice.add(True, label, content)
        with mock.patch(
            "uaclient.files.notices.system.write_file"
        ) as sys_write_file:
            notice.add(True, label, content)
            assert 1 == sys_write_file.call_count

    @pytest.mark.parametrize(
        "label,content",
        (
            (
                FakeNotice.a,
                "notice_a",
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
        notice.add(True, label, content)
        notice.remove(True, label)
        assert [
            mock.call(
                os.path.join(defaults.NOTICES_PERMANENT_DIRECTORY, "01-a"),
            )
        ] == sys_file_absent.call_args_list

    @mock.patch("uaclient.files.notices.system.ensure_file_absent")
    def test_remove_non_root(
        self,
        m_sys_file_absent,
        caplog_text,
    ):
        notice = NoticesManager()
        notice.remove(False, FakeNotice.a)
        assert [] == m_sys_file_absent.call_args_list
        assert "Trying to remove a notice as non-root user" in caplog_text()

    @mock.patch("uaclient.files.notices.NoticesManager.list")
    @mock.patch("uaclient.files.notices.NoticesManager.remove")
    @mock.patch("uaclient.files.notices.NoticesManager.add")
    def test_notice_module(
        self, notice_cls_add, notice_cls_remove, notice_cls_read
    ):
        notices.add(True, FakeNotice.a)
        assert [
            mock.call(True, FakeNotice.a, "notice_a"),
        ] == notice_cls_add.call_args_list
        notices.remove(True, FakeNotice.a)
        assert [
            mock.call(True, FakeNotice.a)
        ] == notice_cls_remove.call_args_list
        notices.list()
        assert 1 == notice_cls_read.call_count
