import mock
import pytest

from uaclient.files.notices import Notice
from uaclient.jobs.update_contract_info import update_contract_info

M_PATH = "uaclient.jobs.update_contract_info."


@mock.patch(M_PATH + "contract.is_contract_changed", return_value=False)
class TestUpdateContractInfo:
    @pytest.mark.parametrize(
        "contract_changed,is_attached",
        (
            (False, True),
            (True, False),
            (True, True),
            (False, False),
        ),
    )
    @mock.patch(M_PATH + "notices", autospec=True)
    def test_is_contract_changed(
        self,
        m_notices,
        m_contract_changed,
        contract_changed,
        is_attached,
        capsys,
        FakeConfig,
    ):
        m_contract_changed.return_value = contract_changed
        if is_attached:
            cfg = FakeConfig().for_attached_machine()
        else:
            cfg = FakeConfig()

        update_contract_info(cfg=cfg)

        if is_attached:
            if contract_changed:
                assert [
                    mock.call(
                        True,
                        Notice.CONTRACT_REFRESH_WARNING,
                    )
                ] == m_notices.add.call_args_list
            else:
                assert [
                    mock.call(
                        True,
                        Notice.CONTRACT_REFRESH_WARNING,
                    )
                ] not in m_notices.add.call_args_list
                print(m_contract_changed.return_value)
                assert [
                    mock.call(True, Notice.CONTRACT_REFRESH_WARNING)
                ] in m_notices.remove.call_args_list
        else:
            assert m_contract_changed.call_count == 0
