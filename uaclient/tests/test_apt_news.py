from datetime import datetime, timedelta, timezone

import mock
import pytest

from uaclient import apt_news, messages
from uaclient.api.u.pro.status.is_attached.v1 import ContractExpiryStatus
from uaclient.clouds.identity import NoCloudTypeReason

M_PATH = "uaclient.apt_news."

NOW = datetime.now(timezone.utc)


class TestAptNews:
    @pytest.mark.parametrize(
        ["selectors", "series", "cloud_type", "attached", "expected"],
        [
            (
                apt_news.AptNewsMessageSelectors(),
                "xenial",
                (None, NoCloudTypeReason.NO_CLOUD_DETECTED),
                False,
                True,
            ),
            (
                apt_news.AptNewsMessageSelectors(
                    codenames=["bionic", "xenial"]
                ),
                "xenial",
                (None, NoCloudTypeReason.NO_CLOUD_DETECTED),
                False,
                True,
            ),
            (
                apt_news.AptNewsMessageSelectors(codenames=["bionic"]),
                "xenial",
                (None, NoCloudTypeReason.NO_CLOUD_DETECTED),
                False,
                False,
            ),
            (
                apt_news.AptNewsMessageSelectors(
                    codenames=["xenial"], pro=True
                ),
                "xenial",
                (None, NoCloudTypeReason.NO_CLOUD_DETECTED),
                False,
                False,
            ),
            (
                apt_news.AptNewsMessageSelectors(
                    codenames=["xenial"], pro=True
                ),
                "xenial",
                (None, NoCloudTypeReason.NO_CLOUD_DETECTED),
                True,
                True,
            ),
            (
                apt_news.AptNewsMessageSelectors(
                    codenames=["bionic"], pro=False
                ),
                "xenial",
                (None, NoCloudTypeReason.NO_CLOUD_DETECTED),
                False,
                False,
            ),
            (
                apt_news.AptNewsMessageSelectors(
                    codenames=["bionic"], pro=False
                ),
                "bionic",
                (None, NoCloudTypeReason.NO_CLOUD_DETECTED),
                False,
                True,
            ),
            (
                apt_news.AptNewsMessageSelectors(
                    codenames=["bionic"],
                    pro=False,
                    clouds=["gce"],
                ),
                "bionic",
                (None, NoCloudTypeReason.NO_CLOUD_DETECTED),
                False,
                False,
            ),
            (
                apt_news.AptNewsMessageSelectors(
                    codenames=["bionic"],
                    pro=False,
                    clouds=["gce"],
                ),
                "bionic",
                (None, NoCloudTypeReason.CLOUD_ID_ERROR),
                False,
                False,
            ),
            (
                apt_news.AptNewsMessageSelectors(
                    codenames=["bionic"],
                    pro=False,
                    clouds=["gce"],
                ),
                "bionic",
                ("aws", None),
                False,
                False,
            ),
            (
                apt_news.AptNewsMessageSelectors(
                    codenames=["bionic"],
                    pro=False,
                    clouds=["gce"],
                ),
                "bionic",
                ("gce", None),
                False,
                True,
            ),
        ],
    )
    @mock.patch(M_PATH + "get_cloud_type")
    @mock.patch(M_PATH + "system.get_release_info")
    def test_do_selectors_apply(
        self,
        m_get_platform_info,
        m_get_cloud_type,
        selectors,
        series,
        cloud_type,
        attached,
        expected,
        FakeConfig,
    ):
        if attached:
            cfg = FakeConfig.for_attached_machine()
        else:
            cfg = FakeConfig()
        m_get_platform_info.return_value = mock.MagicMock(series=series)
        m_get_cloud_type.return_value = cloud_type
        assert expected == apt_news.do_selectors_apply(cfg, selectors)

    @pytest.mark.parametrize(
        ["begin", "end", "expected"],
        [
            (
                NOW + timedelta(days=1),
                None,
                False,
            ),
            (
                NOW - timedelta(days=1),
                None,
                True,
            ),
            (
                NOW - timedelta(days=31),
                None,
                False,
            ),
            (
                NOW - timedelta(days=1),
                NOW + timedelta(days=1),
                True,
            ),
            (
                NOW - timedelta(days=2),
                NOW - timedelta(days=1),
                False,
            ),
        ],
    )
    def test_do_dates_apply(
        self,
        begin,
        end,
        expected,
    ):
        assert expected == apt_news.do_dates_apply(begin, end)

    @pytest.mark.parametrize(
        ["msg", "expected"],
        [
            (
                apt_news.AptNewsMessage(begin=NOW, lines=[]),
                False,
            ),
            (
                apt_news.AptNewsMessage(begin=NOW, lines=["one"]),
                True,
            ),
            (
                apt_news.AptNewsMessage(begin=NOW, lines=["one", "two"]),
                True,
            ),
            (
                apt_news.AptNewsMessage(
                    begin=NOW, lines=["one", "two", "three"]
                ),
                True,
            ),
            (
                apt_news.AptNewsMessage(
                    begin=NOW, lines=["one", "two", "three", "four"]
                ),
                False,
            ),
            (
                apt_news.AptNewsMessage(
                    begin=NOW, lines=["one", "two", "1" * 77]
                ),
                True,
            ),
            (
                apt_news.AptNewsMessage(
                    begin=NOW, lines=["one", "two", "1" * 78]
                ),
                False,
            ),
            (
                apt_news.AptNewsMessage(begin=NOW, lines=["\n"]),
                False,
            ),
            (
                apt_news.AptNewsMessage(
                    begin=NOW, lines=["\033[92mGREEN\033[0m"]
                ),
                False,
            ),
        ],
    )
    def test_is_message_valid(
        self,
        msg,
        expected,
    ):
        assert expected == apt_news.is_message_valid(msg)

    @pytest.mark.parametrize(
        [
            "msg_dicts",
            "is_valid_args",
            "is_valid",
            "dates_apply_args",
            "dates_apply",
            "selectors_apply_args",
            "selectors_apply",
            "expected",
        ],
        [
            (
                [],
                [],
                [],
                [],
                [],
                [],
                [],
                None,
            ),
            (
                [{"invalid": "invalid"}, {"invalid": "invalid"}],
                [],
                [],
                [],
                [],
                [],
                [],
                None,
            ),
            (
                [{"begin": NOW, "lines": ["one"]}],
                [mock.call(apt_news.AptNewsMessage(begin=NOW, lines=["one"]))],
                [False],
                [],
                [],
                [],
                [],
                None,
            ),
            (
                [
                    {"begin": NOW, "lines": ["one"]},
                    {"begin": NOW, "lines": ["two"]},
                ],
                [
                    mock.call(
                        apt_news.AptNewsMessage(begin=NOW, lines=["one"])
                    ),
                    mock.call(
                        apt_news.AptNewsMessage(begin=NOW, lines=["two"])
                    ),
                ],
                [False, True],
                [mock.call(NOW, None)],
                [False],
                [],
                [],
                None,
            ),
            (
                [
                    {"begin": NOW, "lines": ["one"]},
                    {"begin": NOW, "lines": ["two"]},
                    {"begin": NOW, "lines": ["three"]},
                ],
                [
                    mock.call(
                        apt_news.AptNewsMessage(begin=NOW, lines=["one"])
                    ),
                    mock.call(
                        apt_news.AptNewsMessage(begin=NOW, lines=["two"])
                    ),
                    mock.call(
                        apt_news.AptNewsMessage(begin=NOW, lines=["three"])
                    ),
                ],
                [False, True, True],
                [mock.call(NOW, None), mock.call(NOW, None)],
                [False, True],
                [mock.call(mock.ANY, None)],
                [False],
                None,
            ),
            (
                [
                    {"begin": NOW, "lines": ["one"]},
                    {"begin": NOW, "lines": ["two"]},
                    {
                        "begin": NOW,
                        "lines": ["three"],
                        "selectors": {"codenames": ["xenial"]},
                    },
                    {"begin": NOW, "lines": ["four"], "selectors": {}},
                ],
                [
                    mock.call(
                        apt_news.AptNewsMessage(begin=NOW, lines=["one"])
                    ),
                    mock.call(
                        apt_news.AptNewsMessage(begin=NOW, lines=["two"])
                    ),
                    mock.call(
                        apt_news.AptNewsMessage(
                            begin=NOW,
                            lines=["three"],
                            selectors=apt_news.AptNewsMessageSelectors(
                                codenames=["xenial"]
                            ),
                        )
                    ),
                    mock.call(
                        apt_news.AptNewsMessage(
                            begin=NOW,
                            lines=["four"],
                            selectors=apt_news.AptNewsMessageSelectors(),
                        )
                    ),
                ],
                [False, True, True, True],
                [
                    mock.call(NOW, None),
                    mock.call(NOW, None),
                    mock.call(NOW, None),
                ],
                [False, True, True],
                [
                    mock.call(
                        mock.ANY,
                        apt_news.AptNewsMessageSelectors(codenames=["xenial"]),
                    ),
                    mock.call(mock.ANY, apt_news.AptNewsMessageSelectors()),
                ],
                [False, True],
                apt_news.AptNewsMessage(
                    begin=NOW,
                    lines=["four"],
                    selectors=apt_news.AptNewsMessageSelectors(),
                ),
            ),
        ],
    )
    @mock.patch(M_PATH + "do_selectors_apply")
    @mock.patch(M_PATH + "do_dates_apply")
    @mock.patch(M_PATH + "is_message_valid")
    def test_select_messsage(
        self,
        m_is_message_valid,
        m_do_dates_apply,
        m_do_selectors_apply,
        msg_dicts,
        is_valid_args,
        is_valid,
        dates_apply_args,
        dates_apply,
        selectors_apply_args,
        selectors_apply,
        expected,
        FakeConfig,
    ):
        m_is_message_valid.side_effect = is_valid
        m_do_dates_apply.side_effect = dates_apply
        m_do_selectors_apply.side_effect = selectors_apply

        assert expected == apt_news.select_message(FakeConfig(), msg_dicts)

        assert is_valid_args == m_is_message_valid.call_args_list
        assert dates_apply_args == m_do_dates_apply.call_args_list
        assert selectors_apply_args == m_do_selectors_apply.call_args_list

    @pytest.mark.parametrize(
        [
            "apt_news_json",
            "select_message_args",
            "select_message",
            "expected_result",
        ],
        [
            (
                {},
                [mock.call(mock.ANY, [])],
                None,
                None,
            ),
            (
                {"messages": []},
                [mock.call(mock.ANY, [])],
                None,
                None,
            ),
            (
                {"messages": [{"begin": NOW, "lines": ["one", "two"]}]},
                [
                    mock.call(
                        mock.ANY, [{"begin": NOW, "lines": ["one", "two"]}]
                    )
                ],
                apt_news.AptNewsMessage(begin=NOW, lines=["one", "two"]),
                "one\ntwo",
            ),
        ],
    )
    @mock.patch(M_PATH + "select_message")
    @mock.patch(M_PATH + "fetch_aptnews_json")
    def test_fetch_and_process_apt_news(
        self,
        m_fetch_aptnews_json,
        m_select_message,
        apt_news_json,
        select_message_args,
        select_message,
        expected_result,
        FakeConfig,
    ):
        m_fetch_aptnews_json.return_value = apt_news_json
        m_select_message.return_value = select_message

        assert expected_result == apt_news.fetch_and_process_apt_news(
            FakeConfig()
        )

        assert select_message_args == m_select_message.call_args_list

    @pytest.mark.parametrize(
        [
            "expiry_status",
            "remaining_days",
            "expected",
        ],
        [
            (
                ContractExpiryStatus.ACTIVE,
                0,
                None,
            ),
            (
                ContractExpiryStatus.NONE,
                0,
                None,
            ),
            (
                ContractExpiryStatus.ACTIVE_EXPIRED_SOON,
                10,
                messages.CONTRACT_EXPIRES_SOON.pluralize(10).format(
                    remaining_days=10
                ),
            ),
            (
                ContractExpiryStatus.ACTIVE_EXPIRED_SOON,
                15,
                messages.CONTRACT_EXPIRES_SOON.pluralize(15).format(
                    remaining_days=15
                ),
            ),
            (
                ContractExpiryStatus.EXPIRED_GRACE_PERIOD,
                -4,
                messages.CONTRACT_EXPIRED_GRACE_PERIOD.pluralize(10).format(
                    remaining_days=10, expired_date="21 Dec 2012"
                ),
            ),
            (
                ContractExpiryStatus.EXPIRED,
                -15,
                messages.CONTRACT_EXPIRED,
            ),
        ],
    )
    @mock.patch(M_PATH + "_is_attached")
    def test_local_apt_news(
        self,
        m_is_attached,
        expiry_status,
        remaining_days,
        expected,
        FakeConfig,
    ):
        m_is_attached.return_value = mock.MagicMock(
            is_attached=True,
            contract_status=expiry_status.value,
            contract_remaining_days=remaining_days,
        )

        cfg = FakeConfig.for_attached_machine(
            effective_to=datetime(2012, 12, 21, tzinfo=timezone.utc)
        )
        assert expected == apt_news.local_apt_news(cfg)

    @pytest.mark.parametrize(
        ["msg", "expected"],
        [
            (
                "one",
                """\
#
# one
#
""",
            ),
            (
                "one\ntwo",
                """\
#
# one
# two
#
""",
            ),
            (
                "one\ntwo\nthree",
                """\
#
# one
# two
# three
#
""",
            ),
        ],
    )
    def test_format_news_for_apt_update(self, msg, expected):
        assert expected == apt_news.format_news_for_apt_update(msg)

    @pytest.mark.parametrize(
        [
            "local_news",
            "remote_news",
            "expected_formatted_write_calls",
            "expected_raw_write_calls",
            "expected_formatted_delete_calls",
            "expected_raw_delete_calls",
        ],
        [
            (
                [None],
                [None],
                [],
                [],
                [mock.call()],
                [mock.call()],
            ),
            (
                Exception(),
                [None],
                [],
                [],
                [mock.call()],
                [mock.call()],
            ),
            (
                [None],
                Exception(),
                [],
                [],
                [mock.call()],
                [mock.call()],
            ),
            (
                [mock.sentinel.local_news],
                [None],
                [mock.call(mock.sentinel.formatted_news)],
                [mock.call(mock.sentinel.local_news)],
                [],
                [],
            ),
            (
                [None],
                [mock.sentinel.remote_news],
                [mock.call(mock.sentinel.formatted_news)],
                [mock.call(mock.sentinel.remote_news)],
                [],
                [],
            ),
        ],
    )
    @mock.patch(M_PATH + "state_files.apt_news_raw_file.delete")
    @mock.patch(M_PATH + "state_files.apt_news_contents_file.delete")
    @mock.patch(M_PATH + "state_files.apt_news_raw_file.write")
    @mock.patch(M_PATH + "state_files.apt_news_contents_file.write")
    @mock.patch(M_PATH + "format_news_for_apt_update")
    @mock.patch(M_PATH + "fetch_and_process_apt_news")
    @mock.patch(M_PATH + "local_apt_news")
    def test_update_apt_news(
        self,
        m_local_apt_news,
        m_fetch_and_process_apt_news,
        m_format_news_for_apt_update,
        m_formatted_write,
        m_raw_write,
        m_formatted_delete,
        m_raw_delete,
        local_news,
        remote_news,
        expected_formatted_write_calls,
        expected_raw_write_calls,
        expected_formatted_delete_calls,
        expected_raw_delete_calls,
        FakeConfig,
    ):
        m_local_apt_news.side_effect = local_news
        m_fetch_and_process_apt_news.side_effect = remote_news
        m_format_news_for_apt_update.return_value = (
            mock.sentinel.formatted_news
        )

        apt_news.update_apt_news(FakeConfig())

        assert (
            expected_formatted_write_calls == m_formatted_write.call_args_list
        )
        assert expected_raw_write_calls == m_raw_write.call_args_list
        assert (
            expected_formatted_delete_calls
            == m_formatted_delete.call_args_list
        )
        assert expected_raw_delete_calls == m_raw_delete.call_args_list
