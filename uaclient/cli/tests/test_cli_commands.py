import mock
import pytest

from uaclient.cli.commands import (
    ProArgument,
    ProArgumentGroup,
    ProArgumentMutuallyExclusiveGroup,
    ProCommand,
)


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
        mock_argument_group1 = mock.MagicMock()
        mock_argument_group2 = mock.MagicMock()

        mock_subparsers = mock.MagicMock()

        example_command = ProCommand(
            "example",
            help="help",
            description="description",
            argument_groups=[mock_argument_group1, mock_argument_group2],
        )

        example_command.register(mock_subparsers)

        assert [
            mock.call(
                "example",
                help="help",
                description="description",
            )
        ] == mock_subparsers.add_parser.call_args_list
        assert (
            example_command.parser == mock_subparsers.add_parser.return_value
        )
        assert [
            mock.call(example_command.parser)
        ] == mock_argument_group1.register.call_args_list
        assert [
            mock.call(example_command.parser)
        ] == mock_argument_group2.register.call_args_list
        assert [
            mock.call(action=example_command.action)
        ] == example_command.parser.set_defaults.call_args_list

    def test_has_subcommands(self):
        mock_subparsers = mock.MagicMock()

        example_subcommand1 = mock.MagicMock()
        example_subcommand2 = mock.MagicMock()

        example_command = ProCommand(
            "example",
            help="help",
            description="description",
            subcommands=[example_subcommand1, example_subcommand2],
        )

        example_command.register(mock_subparsers)

        inner_subparsers = example_command.parser.add_subparsers.return_value
        assert [
            mock.call(inner_subparsers)
        ] == example_subcommand1.register.call_args_list
        assert [
            mock.call(inner_subparsers)
        ] == example_subcommand2.register.call_args_list


class TestProArgument:
    def test_argument_register(self):
        mock_parser = mock.MagicMock()

        named_argument = ProArgument("mandatory-field", help="help1")
        long_option = ProArgument("--try-this-one", help="help2")
        short_n_long_option = ProArgument(
            "--maybe-short", short_name="-m", help="help3"
        )
        kwargs_included = ProArgument(
            "--one-with-kwargs", help="help4", something="else"
        )

        named_argument.register(mock_parser)
        long_option.register(mock_parser)
        short_n_long_option.register(mock_parser)
        kwargs_included.register(mock_parser)

        assert [
            mock.call("mandatory-field", help="help1"),
            mock.call("--try-this-one", help="help2"),
            mock.call("-m", "--maybe-short", help="help3"),
            mock.call("--one-with-kwargs", help="help4", something="else"),
        ] == mock_parser.add_argument.call_args_list


class TestProArgumentGroup:
    @pytest.mark.parametrize(
        "title,description", (("example", "example_desc"), (None, None))
    )
    def test_argument_group_register_titleless(self, title, description):
        arg1 = mock.MagicMock()
        arg2 = mock.MagicMock()

        me_arg1 = mock.MagicMock()
        me_arg2 = mock.MagicMock()

        mock_parser = mock.MagicMock()

        test_group = ProArgumentGroup(
            title=title,
            description=description,
            arguments=[arg1, arg2],
            mutually_exclusive_groups=[
                ProArgumentMutuallyExclusiveGroup(
                    required=False, arguments=[me_arg1, me_arg2]
                )
            ],
        )

        test_group.register(mock_parser)

        if title and description:
            add_group_args = [mock.call("example", "example_desc")]
            base_parser = mock_parser.add_argument_group.return_value
        else:
            add_group_args = []
            base_parser = mock_parser

        assert add_group_args == mock_parser.add_argument_group.call_args_list

        assert [
            mock.call(required=False)
        ] == base_parser.add_mutually_exclusive_group.call_args_list

        assert [mock.call(base_parser)] == arg1.register.call_args_list
        assert [mock.call(base_parser)] == arg2.register.call_args_list
        assert [
            mock.call(base_parser.add_mutually_exclusive_group.return_value)
        ] == me_arg1.register.call_args_list
        assert [
            mock.call(base_parser.add_mutually_exclusive_group.return_value)
        ] == me_arg2.register.call_args_list
