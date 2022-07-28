import textwrap

import mock
import pytest

from uaclient import messages
from uaclient.cli import (
    action_auto_attach,
    auto_attach_parser,
    get_parser,
    main,
)
from uaclient.exceptions import (
    AlreadyAttachedOnPROError,
    CloudFactoryError,
    CloudFactoryNoCloudError,
    CloudFactoryNonViableCloudError,
    CloudFactoryUnsupportedCloudError,
    LockHeldError,
    NonAutoAttachImageError,
    NonRootUserError,
    UserFacingError,
)

M_PATH = "uaclient.cli."
M_ID_PATH = "uaclient.clouds.identity."

HELP_OUTPUT = textwrap.dedent(
    """\
usage: pro auto-attach [flags]

Automatically attach on an Ubuntu Pro cloud instance.

Flags:
  -h, --help  show this help message and exit
"""
)


@mock.patch(M_PATH + "os.getuid")
def test_non_root_users_are_rejected(getuid, FakeConfig):
    """Check that a UID != 0 will receive a message and exit non-zero"""
    getuid.return_value = 1

    cfg = FakeConfig()
    with pytest.raises(NonRootUserError):
        action_auto_attach(mock.MagicMock(), cfg=cfg)


def fake_instance_factory():
    m_instance = mock.Mock()
    m_instance.identity_doc = "pkcs7-validated-by-backend"
    return m_instance


# For all of these tests we want to appear as root, so mock on the class
@mock.patch(M_PATH + "os.getuid", return_value=0)
class TestActionAutoAttach:
    @mock.patch(M_PATH + "contract.get_available_resources")
    def test_auto_attach_help(self, _m_resources, _getuid, capsys, FakeConfig):
        with pytest.raises(SystemExit):
            with mock.patch(
                "sys.argv", ["/usr/bin/ua", "auto-attach", "--help"]
            ):
                with mock.patch(
                    "uaclient.config.UAConfig",
                    return_value=FakeConfig(),
                ):
                    main()
        out, _err = capsys.readouterr()
        assert HELP_OUTPUT == out

    @mock.patch("uaclient.system.subp")
    def test_lock_file_exists(self, m_subp, _getuid, FakeConfig):
        """Check inability to auto-attach if operation holds lock file."""
        cfg = FakeConfig()
        cfg.write_cache("lock", "123:pro disable")
        with pytest.raises(LockHeldError) as err:
            action_auto_attach(mock.MagicMock(), cfg=cfg)
        assert [mock.call(["ps", "123"])] == m_subp.call_args_list
        assert (
            "Unable to perform: pro auto-attach.\n"
            "Operation in progress: pro disable (pid:123)"
        ) == err.value.msg

    def test_error_if_attached(
        self,
        _m_getuid,
        FakeConfig,
    ):
        cfg = FakeConfig.for_attached_machine()
        with pytest.raises(AlreadyAttachedOnPROError):
            action_auto_attach(mock.MagicMock(), cfg=cfg)

    @pytest.mark.parametrize(
        "features_override", ((None), ({"disable_auto_attach": True}))
    )
    @mock.patch(M_PATH + "_post_cli_attach")
    @mock.patch(M_PATH + "actions.auto_attach")
    @mock.patch(
        M_PATH + "identity.cloud_instance_factory",
        side_effect=fake_instance_factory,
    )
    def test_disable_auto_attach_config(
        self,
        m_cloud_instance_factory,
        m_auto_attach,
        m_post_cli_attach,
        _m_getuid,
        features_override,
        FakeConfig,
    ):
        cfg = FakeConfig()
        if features_override:
            cfg.override_features(features_override)

        ret = action_auto_attach(mock.MagicMock(), cfg=cfg)

        assert 0 == ret
        if features_override:
            assert [] == m_cloud_instance_factory.call_args_list
            assert [] == m_auto_attach.call_args_list
            assert [] == m_post_cli_attach.call_args_list
        else:
            assert [mock.call()] == m_cloud_instance_factory.call_args_list
            assert [
                mock.call(mock.ANY, mock.ANY)
            ] == m_auto_attach.call_args_list
            assert [mock.call(mock.ANY)] == m_post_cli_attach.call_args_list

    @pytest.mark.parametrize(
        "cloud_factory_error, expected_error_cls, expected_error_msg",
        [
            (
                CloudFactoryNoCloudError("test"),
                UserFacingError,
                messages.UNABLE_TO_DETERMINE_CLOUD_TYPE,
            ),
            (
                CloudFactoryNonViableCloudError("test"),
                UserFacingError,
                messages.UNSUPPORTED_AUTO_ATTACH,
            ),
            (
                CloudFactoryUnsupportedCloudError("test"),
                NonAutoAttachImageError,
                messages.UNSUPPORTED_AUTO_ATTACH_CLOUD_TYPE.format(
                    cloud_type="test"
                ),
            ),
            (
                CloudFactoryNoCloudError("test"),
                UserFacingError,
                messages.UNABLE_TO_DETERMINE_CLOUD_TYPE,
            ),
            (
                CloudFactoryError("test"),
                UserFacingError,
                messages.UNABLE_TO_DETERMINE_CLOUD_TYPE,
            ),
        ],
    )
    @mock.patch(M_ID_PATH + "cloud_instance_factory")
    def test_handle_cloud_factory_errors(
        self,
        m_cloud_instance_factory,
        _m_getuid,
        cloud_factory_error,
        expected_error_cls,
        expected_error_msg,
        FakeConfig,
    ):
        """Non-supported clouds will error."""
        m_cloud_instance_factory.side_effect = cloud_factory_error
        cfg = FakeConfig()

        with pytest.raises(expected_error_cls) as excinfo:
            action_auto_attach(mock.MagicMock(), cfg=cfg)

        if expected_error_msg:
            assert expected_error_msg == str(excinfo.value)


class TestParser:
    @mock.patch(M_PATH + "contract.get_available_resources")
    def test_auto_attach_parser_updates_parser_config(
        self, _m_resources, FakeConfig
    ):
        """Update the parser configuration for 'auto-attach'."""
        m_parser = auto_attach_parser(mock.Mock())
        assert "pro auto-attach [flags]" == m_parser.usage
        assert "auto-attach" == m_parser.prog
        assert "Flags" == m_parser._optionals.title

        full_parser = get_parser(FakeConfig())
        with mock.patch("sys.argv", ["pro", "auto-attach"]):
            args = full_parser.parse_args()
        assert "auto-attach" == args.command
        assert "action_auto_attach" == args.action.__name__
