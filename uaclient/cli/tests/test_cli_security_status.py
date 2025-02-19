import mock
import pytest

from uaclient.cli.security_status import security_status_command
from uaclient.util import DatetimeAwareJSONEncoder

M_PATH = "uaclient.cli.security_status."


@mock.patch(M_PATH + "security_status.security_status")
@mock.patch(M_PATH + "security_status.security_status_dict")
@mock.patch("uaclient.contract.get_available_resources")
class TestActionSecurityStatus:
    @pytest.mark.parametrize("output_format", ("json", "yaml", "text"))
    @mock.patch(M_PATH + "safe_dump")
    @mock.patch(M_PATH + "json.dumps")
    def test_action_security_status(
        self,
        m_dumps,
        m_safe_dump,
        _m_resources,
        m_security_status_dict,
        m_security_status,
        output_format,
        FakeConfig,
    ):
        cfg = FakeConfig()
        args = mock.MagicMock()
        args.format = output_format
        args.thirdparty = False
        args.unavailable = False
        args.esm_infra = False
        args.esm_apps = False
        security_status_command.action(args, cfg=cfg)

        if output_format == "json":
            assert m_dumps.call_args_list == [
                mock.call(
                    m_security_status_dict.return_value,
                    sort_keys=True,
                    cls=DatetimeAwareJSONEncoder,
                ),
            ]
            assert m_safe_dump.call_count == 0
        elif output_format == "yaml":
            assert m_safe_dump.call_args_list == [
                mock.call(
                    m_security_status_dict.return_value,
                    default_flow_style=False,
                )
            ]
            assert m_dumps.call_count == 0
        else:
            assert m_dumps.call_count == 0
            assert m_safe_dump.call_count == 0
            assert m_security_status.call_args_list == [mock.call(cfg)]
            assert m_security_status.call_count == 1
