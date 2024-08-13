import mock

from uaclient import defaults
from uaclient.api.u.pro.status.notices.v1 import (
    NoticeInfo,
    NoticeListResult,
    _notices,
)


class TestNoticesApi:
    @mock.patch("uaclient.files.notices.NoticesManager._get_notice_file_names")
    @mock.patch("uaclient.system.load_file")
    def test_notices(self, m_load_file, m_get_notice_file_names, FakeConfig):
        m_get_notice_file_names.side_effect = lambda directory: (
            []
            if directory == defaults.NOTICES_TEMPORARY_DIRECTORY
            else ["1-fakeNotice"]
        )
        m_load_file.return_value = "test"
        expected = NoticeListResult(
            notices=[
                NoticeInfo(
                    order_id="1",
                    label="fakeNotice",
                    message="test",
                )
            ]
        )
        res = _notices(cfg=FakeConfig())
        assert expected == res
