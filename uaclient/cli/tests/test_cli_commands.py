import mock

from uaclient.cli.commands import ProArgument, ProCommand


class TestProCommand:
    def test_command_is_executable(self, FakeConfig):
        mock_action = mock.MagicMock()
        args = mock.MagicMock()
        cfg = FakeConfig()

        no_action_command = ProCommand(
            "example", help="help", description="description"
        )
        action_command = ProCommand(
            "example",
            help="help",
            description="description",
            action=mock_action,
        )

        assert no_action_command.action(args, cfg=cfg) is None
        assert action_command.action(args, cfg=cfg) == mock_action.return_value
        assert [mock.call(args, cfg=cfg)] == mock_action.call_args_list

    def test_command_register(self):
        mock_argument = mock.MagicMock()
        mock_subparsers = mock.MagicMock()

        example_command = ProCommand(
            "example",
            help="help",
            description="description",
            usage="usage",
            arguments=[mock_argument],
        )

        example_command.register(mock_subparsers)

        assert [
            mock.call(
                "example",
                help="help",
                description="description",
                usage="usage",
            )
        ] == mock_subparsers.add_parser.call_args_list
        assert (
            example_command.parser == mock_subparsers.add_parser.return_value
        )
        assert [
            mock.call(example_command.parser)
        ] == mock_argument.register.call_args_list
        assert [
            mock.call(action=example_command.action)
        ] == example_command.parser.set_defaults.call_args_list


class TestProArgument:
    def test_argument_register(self):
        mock_parser = mock.MagicMock()

        named_argument = ProArgument("mandatory-field", help="help1")
        long_option = ProArgument("--try-this-one", help="help2")
        short_n_long_option = ProArgument(
            "--maybe-short", short_name="-m", help="help3"
        )

        named_argument.register(mock_parser)
        long_option.register(mock_parser)
        short_n_long_option.register(mock_parser)

        assert [
            mock.call("mandatory-field", help="help1"),
            mock.call("--try-this-one", help="help2"),
            mock.call("-m", "--maybe-short", help="help3"),
        ] == mock_parser.add_argument.call_args_list
