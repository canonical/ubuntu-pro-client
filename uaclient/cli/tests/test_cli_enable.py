from argparse import Namespace
from typing import Any

import mock
import pytest

from uaclient import exceptions, messages
from uaclient.api.u.pro.services.dependencies.v1 import (
    DependenciesResult,
    ServiceWithDependencies,
    ServiceWithReason,
)

from uaclient.api.u.pro.services.enable.v1 import EnableOptions, EnableResult
from uaclient.api.u.pro.services.enabled.v1 import (  # type: ignore[import]
    EnabledService,  # type: ignore[misc]
    EnabledServicesResult,  # type: ignore[misc]
)
from uaclient.api.u.pro.status.is_attached.v1 import IsAttachedResult
from uaclient.cli.enable import (
    _enable_landscape,  # type: ignore[attr-defined]
    _enable_one_service,  # type: ignore[attr-defined]
    _EnableOneServiceResult,  # type: ignore[attr-defined]
    _print_json_output,  # type: ignore[attr-defined]
    enable_command,
    prompt_for_dependency_handling,
)
from uaclient.testing.helpers import does_not_raise


class TestActionEnable:
    @pytest.mark.parametrize(  # type: ignore[misc]
        "is_attached,args,kwargs,refresh_side_effect,valid_entitlement_names,enabled_services,dependencies,entitlements_for_enabling,enable_one_service_side_effect,expected_enable_one_service_calls,expected_print_json_output_calls,expected_raises",
        (  # type: ignore[misc]
            # assume-yes required for json output
            (
                IsAttachedResult(
                    is_attached=True,
                    contract_status="",
                    contract_remaining_days=100,
                    is_attached_and_contract_valid=True,
                ),
                Namespace(
                    format="json",
                    variant="",
                    access_only=False,
                    assume_yes=False,
                    auto=False,
                ),
                {},
                None,
                None,
                None,
                None,
                None,
                None,
                [],
                [],
                pytest.raises(exceptions.CLIJSONFormatRequireAssumeYes),
            ),
            # variant + access-only not allowed
            (
                IsAttachedResult(
                    is_attached=True,
                    contract_status="",
                    contract_remaining_days=100,
                    is_attached_and_contract_valid=True,
                ),
                Namespace(
                    format="cli",
                    variant="variant",
                    access_only=True,
                    assume_yes=False,
                    auto=False,
                ),
                {},
                None,
                None,
                None,
                None,
                None,
                None,
                [],
                [],
                pytest.raises(exceptions.InvalidOptionCombination),
            ),
            # variant + auto not allowed
            (
                IsAttachedResult(
                    is_attached=True,
                    contract_status="",
                    contract_remaining_days=100,
                    is_attached_and_contract_valid=True,
                ),
                Namespace(
                    format="cli",
                    variant="variant",
                    access_only=False,
                    assume_yes=False,
                    auto=True,
                ),
                {},
                None,
                None,
                None,
                None,
                None,
                None,
                [],
                [],
                pytest.raises(exceptions.InvalidOptionCombination),
            ),
            # access_only + auto not allowed
            (
                IsAttachedResult(
                    is_attached=True,
                    contract_status="",
                    contract_remaining_days=100,
                    is_attached_and_contract_valid=True,
                ),
                Namespace(
                    format="cli",
                    variant="",
                    access_only=True,
                    assume_yes=False,
                    auto=True,
                ),
                {},
                None,
                None,
                None,
                None,
                None,
                None,
                [],
                [],
                pytest.raises(exceptions.InvalidOptionCombination),
            ),
            # contract not valid
            (
                IsAttachedResult(
                    is_attached=True,
                    contract_status="",
                    contract_remaining_days=100,
                    is_attached_and_contract_valid=False,
                ),
                Namespace(
                    format="cli",
                    variant="",
                    access_only=False,
                    assume_yes=False,
                    auto=False,
                ),
                {},
                None,
                None,
                None,
                None,
                None,
                None,
                [],
                [
                    mock.call(
                        False,
                        {"_schema_version": "0.1", "needs_reboot": False},
                        [],
                        [],
                        [
                            {
                                "type": "system",
                                "message": messages.E_CONTRACT_EXPIRED.msg,
                                "message_code": messages.E_CONTRACT_EXPIRED.name,  # noqa: E501
                            }
                        ],
                        [],
                        success=False,
                    )
                ],
                does_not_raise(),
            ),
            # contract not valid, json output
            (
                IsAttachedResult(
                    is_attached=True,
                    contract_status="",
                    contract_remaining_days=100,
                    is_attached_and_contract_valid=False,
                ),
                Namespace(
                    format="json",
                    variant="",
                    access_only=False,
                    assume_yes=True,
                    auto=False,
                ),
                {},
                None,
                None,
                None,
                None,
                None,
                None,
                [],
                [
                    mock.call(
                        True,
                        {"_schema_version": "0.1", "needs_reboot": False},
                        [],
                        [],
                        [
                            {
                                "type": "system",
                                "message": messages.E_CONTRACT_EXPIRED.msg,
                                "message_code": messages.E_CONTRACT_EXPIRED.name,  # noqa: E501
                            }
                        ],
                        [],
                        success=False,
                    )
                ],
                does_not_raise(),
            ),
            # contract not valid, json output, contract refresh warning
            (
                IsAttachedResult(
                    is_attached=True,
                    contract_status="",
                    contract_remaining_days=100,
                    is_attached_and_contract_valid=False,
                ),
                Namespace(
                    format="json",
                    variant="",
                    access_only=False,
                    assume_yes=True,
                    auto=False,
                ),
                {},
                exceptions.ConnectivityError(cause=Exception(), url=""),
                None,
                None,
                None,
                None,
                None,
                [],
                [
                    mock.call(
                        True,
                        {"_schema_version": "0.1", "needs_reboot": False},
                        [],
                        [],
                        [
                            {
                                "type": "system",
                                "message": messages.E_CONTRACT_EXPIRED.msg,
                                "message_code": messages.E_CONTRACT_EXPIRED.name,  # noqa: E501
                            }
                        ],
                        [
                            {
                                "type": "system",
                                "message": messages.E_REFRESH_CONTRACT_FAILURE.msg,  # noqa: E501
                                "message_code": messages.E_REFRESH_CONTRACT_FAILURE.name,  # noqa: E501
                            }
                        ],
                        success=False,
                    )
                ],
                does_not_raise(),
            ),
            # success multiple services, one needs reboot
            (
                IsAttachedResult(
                    is_attached=True,
                    contract_status="",
                    contract_remaining_days=100,
                    is_attached_and_contract_valid=True,
                ),
                Namespace(
                    service=["one", "two", "three"],
                    format="json",
                    variant="",
                    access_only=False,
                    assume_yes=True,
                    auto=False,
                ),
                {},
                None,
                (["one", "two", "three"], []),
                EnabledServicesResult(enabled_services=[]),
                DependenciesResult(services=[]),
                ["three", "two", "one"],
                [
                    _EnableOneServiceResult(
                        success=True, needs_reboot=False, error=None
                    ),
                    _EnableOneServiceResult(
                        success=True, needs_reboot=True, error=None
                    ),
                    _EnableOneServiceResult(
                        success=True, needs_reboot=False, error=None
                    ),
                ],
                [
                    mock.call(
                        mock.ANY,
                        "three",
                        "",
                        False,
                        True,
                        True,
                        None,
                        [],
                        [],
                    ),
                    mock.call(
                        mock.ANY,
                        "two",
                        "",
                        False,
                        True,
                        True,
                        None,
                        [],
                        mock.sentinel.dependencies,
                    ),
                    mock.call(
                        mock.ANY,
                        "one",
                        "",
                        False,
                        True,
                        True,
                        None,
                        [],
                        mock.sentinel.dependencies,
                    ),
                ],
                [
                    mock.call(
                        True,
                        {"_schema_version": "0.1", "needs_reboot": True},
                        ["three", "two", "one"],
                        [],
                        [],
                        [],
                        success=True,
                    )
                ],
                does_not_raise(),
            ),
            # some services not found
            (
                IsAttachedResult(
                    is_attached=True,
                    contract_status="",
                    contract_remaining_days=100,
                    is_attached_and_contract_valid=True,
                ),
                Namespace(
                    service=["one", "two", "three"],
                    format="json",
                    variant="",
                    access_only=False,
                    assume_yes=True,
                    auto=False,
                ),
                {},
                None,
                (["two"], ["one", "three"]),
                EnabledServicesResult(enabled_services=[]),
                DependenciesResult(services=[]),
                ["two"],
                [
                    _EnableOneServiceResult(
                        success=True, needs_reboot=False, error=None
                    ),
                ],
                [
                    mock.call(
                        mock.ANY,
                        "two",
                        "",
                        False,
                        True,
                        True,
                        None,
                        [],
                        mock.sentinel.dependencies,
                    ),
                ],
                [
                    mock.call(
                        True,
                        {"_schema_version": "0.1", "needs_reboot": False},
                        ["two"],
                        ["one", "three"],
                        [
                            {
                                "type": "system",
                                "service": None,
                                "message": mock.ANY,
                                "message_code": "invalid-service-or-failure",
                                "additional_info": {
                                    "operation": "enable",
                                    "invalid_service": "one, three",
                                    "service_msg": mock.ANY,
                                },
                            }
                        ],
                        [],
                        success=False,
                    )
                ],
                does_not_raise(),
            ),
            # one success, one fail, one not found
            (
                IsAttachedResult(
                    is_attached=True,
                    contract_status="",
                    contract_remaining_days=100,
                    is_attached_and_contract_valid=True,
                ),
                Namespace(
                    service=["one", "two", "three"],
                    format="json",
                    variant="",
                    access_only=False,
                    assume_yes=True,
                    auto=False,
                ),
                {},
                None,
                (["one", "two"], ["three"]),
                EnabledServicesResult(enabled_services=[]),
                DependenciesResult(services=[]),
                ["two", "one"],
                [
                    _EnableOneServiceResult(
                        success=False,
                        needs_reboot=False,
                        error={"test": "error"},
                    ),
                    _EnableOneServiceResult(
                        success=True, needs_reboot=False, error=None
                    ),
                ],
                [
                    mock.call(
                        mock.ANY,
                        "two",
                        "",
                        False,
                        True,
                        True,
                        None,
                        [],
                        mock.sentinel.dependencies,
                    ),
                    mock.call(
                        mock.ANY,
                        "one",
                        "",
                        False,
                        True,
                        True,
                        None,
                        [],
                        mock.sentinel.dependencies,
                    ),
                ],
                [
                    mock.call(
                        True,
                        {"_schema_version": "0.1", "needs_reboot": False},
                        ["one"],
                        ["two", "three"],
                        [
                            {"test": "error"},
                            {
                                "type": "system",
                                "service": None,
                                "message": mock.ANY,
                                "message_code": "invalid-service-or-failure",
                                "additional_info": {
                                    "operation": "enable",
                                    "invalid_service": "three",
                                    "service_msg": mock.ANY,
                                },
                            },
                        ],
                        [],
                        success=False,
                    )
                ],
                does_not_raise(),
            ),
        ),
    )
    @mock.patch("uaclient.contract.UAContractClient.update_activity_token")
    @mock.patch("uaclient.cli.enable._enable_one_service")
    @mock.patch("uaclient.entitlements.order_entitlements_for_enabling")
    @mock.patch("uaclient.cli.enable._dependencies")
    @mock.patch("uaclient.cli.enable._enabled_services")
    @mock.patch("uaclient.entitlements.get_valid_entitlement_names")
    @mock.patch("uaclient.cli.enable._print_json_output")
    @mock.patch("uaclient.contract.refresh")
    @mock.patch("uaclient.cli.cli_util.create_interactive_only_print_function")
    @mock.patch("uaclient.util.we_are_currently_root", return_value=True)
    @mock.patch("uaclient.cli.enable._is_attached")
    def test_action_enable(
        self,
        m_is_attached,  # type: ignore
        m_we_are_currently_root,  # type: ignore
        m_create_interactive_only_print_function,  # type: ignore
        m_refresh,  # type: ignore
        m_print_json_output,  # type: ignore
        m_get_valid_entitlement_names,  # type: ignore
        m_enabled_services,  # type: ignore
        m_dependencies,  # type: ignore
        m_order_entitlements_for_enabling,  # type: ignore
        m_enable_one_service,  # type: ignore
        m_update_activity_token,  # type: ignore
        is_attached,  # type: ignore
        args,  # type: ignore
        kwargs,  # type: ignore
        refresh_side_effect,  # type: ignore
        valid_entitlement_names,  # type: ignore
        enabled_services,  # type: ignore
        dependencies,  # type: ignore
        entitlements_for_enabling,  # type: ignore
        enable_one_service_side_effect,  # type: ignore
        expected_enable_one_service_calls,  # type: ignore
        expected_print_json_output_calls,  # type: ignore
        expected_raises,  # type: ignore
        FakeConfig,  # type: ignore
        fake_machine_token_file,  # type: ignore
    ):
        m_is_attached.return_value = is_attached
        m_refresh.side_effect = refresh_side_effect
        m_get_valid_entitlement_names.return_value = valid_entitlement_names
        m_enabled_services.return_value = enabled_services
        m_dependencies.return_value = dependencies
        m_order_entitlements_for_enabling.return_value = (
            entitlements_for_enabling
        )
        m_enable_one_service.side_effect = enable_one_service_side_effect
        fake_machine_token_file.attached = True

        with expected_raises:
            enable_command.action(args, cfg=FakeConfig(), **kwargs)  # type: ignore[misc]

        assert (
            expected_enable_one_service_calls
            == m_enable_one_service.call_args_list  # type: ignore[misc]
        )
        assert (
            expected_print_json_output_calls
            == m_print_json_output.call_args_list  # type: ignore[misc]
        )

    @mock.patch("uaclient.contract.UAContractClient.update_activity_token")
    @mock.patch("uaclient.cli.enable._enable_one_service")
    @mock.patch("uaclient.cli.enable._dependencies")
    @mock.patch("uaclient.cli.enable._enabled_services")
    @mock.patch(
        "uaclient.cli.enable.contract.get_enabled_by_default_services"
    )
    @mock.patch("uaclient.cli.enable._print_json_output")
    @mock.patch("uaclient.contract.refresh")
    @mock.patch("uaclient.cli.cli_util.create_interactive_only_print_function")
    @mock.patch("uaclient.util.we_are_currently_root", return_value=True)
    @mock.patch("uaclient.cli.enable._is_attached")
    def test_action_enable_auto_json_success(
        self,
        m_is_attached: mock.Mock,
        _m_we_are_currently_root: mock.Mock,
        m_create_interactive_only_print_function: mock.Mock,
        m_refresh: mock.Mock,
        m_print_json_output: mock.Mock,
        m_get_enabled_by_default_services: mock.Mock,
        m_enabled_services: mock.Mock,
        m_dependencies: mock.Mock,
        m_enable_one_service: mock.Mock,
        m_update_activity_token: mock.Mock,
        FakeConfig: Any,
        fake_machine_token_file: Any,
    ) -> None:
        m_is_attached.return_value = IsAttachedResult(
            is_attached=True,
            contract_status="",
            contract_remaining_days=100,
            is_attached_and_contract_valid=True,
        )
        m_create_interactive_only_print_function.return_value = mock.Mock()
        m_refresh.side_effect = None

        # Set up fake machine token to be attached
        fake_machine_token_file.attached = True
        fake_machine_token_file.token = {"some": "data"}

        service_one = mock.Mock()
        service_one.name = "esm-infra"
        service_two = mock.Mock()
        service_two.name = "livepatch"
        m_get_enabled_by_default_services.return_value = [
            service_one,
            service_two,
        ]

        fake_machine_token_file.entitlements = mock.Mock(
            return_value=mock.sentinel.entitlements
        )

        m_enabled_services.return_value = EnabledServicesResult(
            enabled_services=[],
        )
        m_dependencies.return_value = DependenciesResult(services=[])
        m_enable_one_service.side_effect = [
            _EnableOneServiceResult(True, False, None),
            _EnableOneServiceResult(True, True, None),
        ]

        args = Namespace(
            service=[],
            format="json",
            variant="",
            access_only=False,
            assume_yes=True,
            auto=True,
        )

        ret = enable_command.action(args, cfg=FakeConfig())  # type: ignore[misc]

        assert ret == 0
        assert m_enable_one_service.call_args_list == [  # type: ignore[misc]
            mock.call(
                cfg=mock.ANY,
                ent_name="esm-infra",
                variant="",
                access_only=False,
                assume_yes=True,
                json_output=True,
                extra_args=None,
                enabled_services=[],
                all_dependencies=[],
            ),
            mock.call(
                cfg=mock.ANY,
                ent_name="livepatch",
                variant="",
                access_only=False,
                assume_yes=True,
                json_output=True,
                extra_args=None,
                enabled_services=[],
                all_dependencies=[],
            ),
        ]
        assert m_print_json_output.call_args_list == [  # type: ignore[misc]
            mock.call(
                True,
                {"_schema_version": "0.1", "needs_reboot": True},
                ["esm-infra", "livepatch"],
                [],
                [],
                [],
                success=True,
            )
        ]
        m_get_enabled_by_default_services.assert_called_once_with(  # type: ignore[misc]
            mock.ANY, mock.sentinel.entitlements
        )
        m_update_activity_token.assert_called_once_with()  # type: ignore[misc]

    @mock.patch("uaclient.contract.UAContractClient.update_activity_token")
    @mock.patch("uaclient.cli.enable._enable_one_service")
    @mock.patch("uaclient.cli.enable._dependencies")
    @mock.patch("uaclient.cli.enable._enabled_services")
    @mock.patch(
        "uaclient.cli.enable.contract.get_enabled_by_default_services"
    )
    @mock.patch("uaclient.cli.enable._print_json_output")
    @mock.patch("uaclient.contract.refresh")
    @mock.patch("uaclient.cli.cli_util.create_interactive_only_print_function")
    @mock.patch("uaclient.util.we_are_currently_root", return_value=True)
    @mock.patch("uaclient.cli.enable._is_attached")
    def test_action_enable_auto_json_failure(
        self,
        m_is_attached,  # type: ignore
        _m_we_are_currently_root,  # type: ignore
        m_create_interactive_only_print_function,  # type: ignore
        m_refresh,  # type: ignore
        m_print_json_output,  # type: ignore
        m_get_enabled_by_default_services,  # type: ignore
        m_enabled_services,  # type: ignore
        m_dependencies,  # type: ignore
        m_enable_one_service,  # type: ignore
        m_update_activity_token,  # type: ignore
        FakeConfig,  # type: ignore
        fake_machine_token_file,  # type: ignore
    ):
        m_is_attached.return_value = IsAttachedResult(
            is_attached=True,
            contract_status="",
            contract_remaining_days=100,
            is_attached_and_contract_valid=True,
        )
        m_create_interactive_only_print_function.return_value = mock.Mock()
        m_refresh.side_effect = None

        # Set up fake machine token to be attached
        fake_machine_token_file.attached = True
        fake_machine_token_file.token = {"some": "data"}

        service_one = mock.Mock()
        service_one.name = "esm-infra"
        service_two = mock.Mock()
        service_two.name = "livepatch"
        m_get_enabled_by_default_services.return_value = [
            service_one,
            service_two,
        ]

        fake_machine_token_file.entitlements = mock.Mock(
            return_value=mock.sentinel.entitlements
        )

        m_enabled_services.return_value = EnabledServicesResult(
            enabled_services=[],
        )
        m_dependencies.return_value = DependenciesResult(services=[])
        m_enable_one_service.side_effect = [
            _EnableOneServiceResult(True, False, None),
            _EnableOneServiceResult(
                False,
                False,
                {
                    "type": "service",
                    "service": "livepatch",
                    "message": "failure",
                    "message_code": "error",
                },
            ),
        ]

        args = Namespace(
            service=[],
            format="json",
            variant="",
            access_only=False,
            assume_yes=True,
            auto=True,
        )

        ret = enable_command.action(args, cfg=FakeConfig())  # type: ignore[misc]

        assert ret == 1
        assert m_print_json_output.call_args_list == [  # type: ignore[misc]
            mock.call(
                True,
                {"_schema_version": "0.1", "needs_reboot": False},
                ["esm-infra"],
                ["livepatch"],
                [
                    {
                        "type": "service",
                        "service": "livepatch",
                        "message": "failure",
                        "message_code": "error",
                    }
                ],
                [],
                success=False,
            )
        ]
        m_get_enabled_by_default_services.assert_called_once_with(  # type: ignore[misc]
            mock.ANY, mock.sentinel.entitlements
        )
        m_update_activity_token.assert_called_once_with()  # type: ignore[misc]

    @mock.patch("uaclient.contract.UAContractClient.update_activity_token")
    @mock.patch("uaclient.cli.enable._enable_one_service")
    @mock.patch("uaclient.cli.enable._dependencies")
    @mock.patch("uaclient.cli.enable._enabled_services")
    @mock.patch(
        "uaclient.cli.enable.contract.get_enabled_by_default_services"
    )
    @mock.patch("uaclient.cli.enable._print_json_output")
    @mock.patch("uaclient.contract.refresh")
    @mock.patch("uaclient.cli.cli_util.create_interactive_only_print_function")
    @mock.patch("uaclient.util.we_are_currently_root", return_value=True)
    @mock.patch("uaclient.cli.enable._is_attached")
    def test_action_enable_auto_json_no_services(
        self,
        m_is_attached,  # type: ignore
        _m_we_are_currently_root,  # type: ignore
        m_create_interactive_only_print_function,  # type: ignore
        m_refresh,  # type: ignore
        m_print_json_output,  # type: ignore
        m_get_enabled_by_default_services,  # type: ignore
        m_enabled_services,  # type: ignore
        m_dependencies,  # type: ignore
        m_enable_one_service,  # type: ignore
        m_update_activity_token,  # type: ignore
        FakeConfig,  # type: ignore
        fake_machine_token_file,  # type: ignore
    ):
        m_is_attached.return_value = IsAttachedResult(
            is_attached=True,
            contract_status="",
            contract_remaining_days=100,
            is_attached_and_contract_valid=True,
        )
        m_create_interactive_only_print_function.return_value = mock.Mock()
        m_refresh.side_effect = None

        # Set up fake machine token to be attached
        fake_machine_token_file.attached = True
        fake_machine_token_file.token = {"some": "data"}

        m_get_enabled_by_default_services.return_value = []

        fake_machine_token_file.entitlements = mock.Mock(
            return_value=mock.sentinel.entitlements
        )

        m_enabled_services.return_value = EnabledServicesResult(
            enabled_services=[],
        )
        m_dependencies.return_value = DependenciesResult(services=[])
        m_enable_one_service.return_value = _EnableOneServiceResult(
            success=True,
            needs_reboot=False,
            error=None,
        )

        args = Namespace(
            service=[],
            format="json",
            variant="",
            access_only=False,
            assume_yes=True,
            auto=True,
        )

        ret = enable_command.action(args, cfg=FakeConfig())  # type: ignore[misc]

        assert ret == 0
        m_enable_one_service.assert_not_called()  # type: ignore[misc]  # type: ignore[misc]
        assert m_print_json_output.call_args_list == [  # type: ignore[misc]
            mock.call(
                True,
                {"_schema_version": "0.1", "needs_reboot": False},
                [],
                [],
                [],
                [
                    {
                        "type": "system",
                        "message": messages.NO_SERVICES_TO_AUTO_ENABLE,
                        "message_code": "no-services-to-auto-enable",
                    }
                ],
                success=True,
            )
        ]
        m_get_enabled_by_default_services.assert_called_once_with(  # type: ignore[misc]
            mock.ANY, mock.sentinel.entitlements
        )
        m_update_activity_token.assert_called_once_with()  # type: ignore[misc]

    @pytest.mark.parametrize(
        [
            "kwargs",
            "prompt_for_dependency_handling_side_effect",
            "enable_landscape_result",
            "enable_result",
            "expected_prompt_for_dependency_handling_calls",
            "expected_enable_landscape_calls",
            "expected_enable_calls",
            "expected_status_calls",
            "expected_result",
        ],
        (
            # already enabled
            (
                {
                    "ent_name": "one",
                    "variant": "",
                    "access_only": False,
                    "assume_yes": False,
                    "json_output": False,
                    "extra_args": None,
                    "enabled_services": [EnabledService(name="one")],
                    "all_dependencies": [],
                },
                None,
                None,
                None,
                [],
                [],
                [],
                [],
                _EnableOneServiceResult(
                    success=False,
                    needs_reboot=False,
                    error={
                        "type": "service",
                        "service": "one",
                        "message": messages.ALREADY_ENABLED.format(  # type: ignore[misc]
                            title=mock.sentinel.ent_title
                        ).msg,
                        "message_code": "service-already-enabled",
                    },
                ),
            ),
            # prompt denied fails
            (
                {
                    "ent_name": "one",
                    "variant": "",
                    "access_only": False,
                    "assume_yes": False,
                    "json_output": False,
                    "extra_args": None,
                    "enabled_services": [],
                    "all_dependencies": [],
                },
                [exceptions.PromptDeniedError()],
                None,
                None,
                [
                    mock.call(
                        mock.ANY,
                        "one",
                        [],
                        [],
                        called_name="one",
                        variant="",
                        service_title=mock.sentinel.ent_title,
                    )
                ],
                [],
                [],
                [],
                _EnableOneServiceResult(
                    success=False, needs_reboot=False, error=None
                ),
            ),
            # landscape
            (
                {
                    "ent_name": "landscape",
                    "variant": "",
                    "access_only": False,
                    "assume_yes": mock.sentinel.assume_yes,
                    "json_output": False,
                    "extra_args": None,
                    "enabled_services": [],
                    "all_dependencies": [],
                },
                None,
                EnableResult(
                    enabled=["landscape"],
                    disabled=[],
                    reboot_required=True,
                    messages=[],
                ),
                None,
                [],
                [
                    mock.call(
                        mock.ANY,
                        False,
                        extra_args=None,
                        progress_object=mock.sentinel.cli_progress,
                    )
                ],
                [],
                [mock.call(cfg=mock.ANY)],
                _EnableOneServiceResult(
                    success=True, needs_reboot=True, error=None
                ),
            ),
            # non-landscape
            (
                {
                    "ent_name": "one",
                    "variant": "test_variant",
                    "access_only": False,
                    "assume_yes": mock.sentinel.assume_yes,
                    "json_output": False,
                    "extra_args": None,
                    "enabled_services": [],
                    "all_dependencies": [],
                },
                None,
                None,
                EnableResult(
                    enabled=["one"],
                    disabled=[],
                    reboot_required=True,
                    messages=[],
                ),
                [],
                [],
                [
                    mock.call(
                        EnableOptions(
                            service="one",
                            variant="test_variant",
                            access_only=False,
                        ),
                        mock.ANY,
                        progress_object=mock.sentinel.cli_progress,
                    )
                ],
                [mock.call(cfg=mock.ANY)],
                _EnableOneServiceResult(
                    success=True, needs_reboot=True, error=None
                ),
            ),
            # json output
            (
                {
                    "ent_name": "one",
                    "variant": "test_variant",
                    "access_only": False,
                    "assume_yes": mock.sentinel.assume_yes,
                    "json_output": True,
                    "extra_args": None,
                    "enabled_services": [],
                    "all_dependencies": [],
                },
                None,
                None,
                EnableResult(
                    enabled=["one"],
                    disabled=[],
                    reboot_required=True,
                    messages=[],
                ),
                [],
                [],
                [
                    mock.call(
                        EnableOptions(
                            service="one",
                            variant="test_variant",
                            access_only=False,
                        ),
                        mock.ANY,
                        progress_object=None,
                    )
                ],
                [mock.call(cfg=mock.ANY)],
                _EnableOneServiceResult(
                    success=True, needs_reboot=True, error=None
                ),
            ),
        ),
    )
    @mock.patch("uaclient.status.status")
    @mock.patch("uaclient.cli.enable._enable")
    @mock.patch("uaclient.cli.enable._enable_landscape")
    @mock.patch("uaclient.cli.enable.cli_util.CLIEnableDisableProgress")
    @mock.patch("uaclient.cli.enable.prompt_for_dependency_handling")
    @mock.patch("uaclient.cli.enable.entitlements.entitlement_factory")
    @mock.patch("uaclient.cli.cli_util.create_interactive_only_print_function")
    def test_enable_one_service(
        self,
        m_create_interactive_only_print_function,  # type: ignore
        m_entitlement_factory,  # type: ignore
        m_prompt_for_dependency_handling,  # type: ignore
        m_progress_class,  # type: ignore
        m_enable_landscape,  # type: ignore
        m_enable,  # type: ignore
        m_status,  # type: ignore
        kwargs,  # type: ignore
        prompt_for_dependency_handling_side_effect,  # type: ignore
        enable_landscape_result,  # type: ignore
        enable_result,  # type: ignore
        expected_prompt_for_dependency_handling_calls,  # type: ignore
        expected_enable_landscape_calls,  # type: ignore
        expected_enable_calls,  # type: ignore
        expected_status_calls,  # type: ignore
        expected_result,  # type: ignore
        FakeConfig,  # type: ignore
    ):
        mock_ent = mock.MagicMock()
        m_entitlement_factory.return_value = mock_ent
        mock_ent.name = kwargs.get("ent_name")  # type: ignore[misc]
        mock_ent.title = mock.sentinel.ent_title
        m_prompt_for_dependency_handling.side_effect = (
            prompt_for_dependency_handling_side_effect
        )
        m_progress_class.return_value = mock.sentinel.cli_progress
        m_enable_landscape.return_value = enable_landscape_result
        m_enable.return_value = enable_result

        assert expected_result == _enable_one_service(FakeConfig(), **kwargs)  # type: ignore[misc]

        assert (
            expected_prompt_for_dependency_handling_calls
            == m_prompt_for_dependency_handling.call_args_list  # type: ignore[misc]
        )
        assert (
            expected_enable_landscape_calls
            == m_enable_landscape.call_args_list  # type: ignore[misc]
        )
        assert expected_enable_calls == m_enable.call_args_list  # type: ignore[misc]
        assert expected_status_calls == m_status.call_args_list  # type: ignore[misc]

    @pytest.mark.parametrize(
        [
            "enable_side_effect",
            "expected_raises",
            "expected_result",
        ],
        (
            (
                exceptions.LandscapeConfigFailed(),
                pytest.raises(exceptions.LandscapeConfigFailed),
                None,
            ),
            (
                [(False, None)],
                pytest.raises(exceptions.EntitlementNotEnabledError),
                None,
            ),
            (
                [(True, None)],
                does_not_raise(),
                EnableResult(
                    enabled=["landscape"],
                    disabled=[],
                    reboot_required=False,
                    messages=[],
                ),
            ),
        ),
    )
    @mock.patch("uaclient.cli.enable.lock.RetryLock")
    @mock.patch("uaclient.cli.enable.entitlements.LandscapeEntitlement")
    def test_enable_landscape(
        self,
        m_landscape_entitlement,  # type: ignore
        m_lock,  # type: ignore
        enable_side_effect,  # type: ignore
        expected_raises,  # type: ignore
        expected_result,  # type: ignore
        FakeConfig,  # type: ignore
    ):
        m_enable = m_landscape_entitlement.return_value.enable  # type: ignore[misc]
        m_enable.side_effect = enable_side_effect
        with expected_raises:
            assert expected_result == _enable_landscape(
                FakeConfig,  # type: ignore[misc]
                False,
                None,
                None,
            )
        assert [
            mock.call(
                mock.ANY,
                called_name="landscape",
                access_only=False,
                extra_args=None,
            )
        ] == m_landscape_entitlement.call_args_list  # type: ignore[misc]

    @pytest.mark.parametrize(
        [
            "json_output",
            "expected_print_calls",
        ],
        (
            (True, [mock.call(mock.ANY)]),
            (False, []),
        ),
    )
    @mock.patch("builtins.print")
    def test_print_json_output(
        self, m_print, json_output, expected_print_calls  # type: ignore
    ):
        _print_json_output(json_output, {}, [], [], [], [], True)  # type: ignore[misc]
        assert expected_print_calls == m_print.call_args_list  # type: ignore[misc]


class TestPromptForDependencyHandling:
    @pytest.mark.parametrize(  # type: ignore[misc]
        [
            "service",
            "all_dependencies",
            "enabled_services",
            "called_name",
            "service_title",
            "variant",
            "cfg_block_disable_on_enable",
            "prompt_side_effects",
            "expected_prompts",
            "expected_raise",
        ],
        [  # type: ignore[misc]
            # no dependencies
            (
                "one",
                [
                    ServiceWithDependencies(
                        name="one", incompatible_with=[], depends_on=[]
                    )
                ],
                [],
                "one",
                "One",
                "",
                False,
                [],
                [],
                does_not_raise(),
            ),
            # incompatible with "two", but two not enabled
            (
                "one",
                [
                    ServiceWithDependencies(
                        name="one",
                        incompatible_with=[
                            ServiceWithReason(
                                name="two", reason=mock.MagicMock()
                            )
                        ],
                        depends_on=[],
                    )
                ],
                [],
                "one",
                "One",
                "",
                False,
                [],
                [],
                does_not_raise(),
            ),
            # incompatible with "two", two enabled, successful prompt
            (
                "one",
                [
                    ServiceWithDependencies(
                        name="one",
                        incompatible_with=[
                            ServiceWithReason(
                                name="two", reason=mock.MagicMock()
                            )
                        ],
                        depends_on=[],
                    )
                ],
                [EnabledService(name="two")],
                "one",
                "One",
                "",
                False,
                [True],
                [mock.call(msg=mock.ANY)],
                does_not_raise(),
            ),
            # incompatible with "two", two enabled, cfg denies
            (
                "one",
                [
                    ServiceWithDependencies(
                        name="one",
                        incompatible_with=[
                            ServiceWithReason(
                                name="two", reason=mock.MagicMock()
                            )
                        ],
                        depends_on=[],
                    )
                ],
                [EnabledService(name="two")],
                "one",
                "One",
                "",
                True,
                [],
                [],
                pytest.raises(exceptions.IncompatibleServiceStopsEnable),
            ),
            # incompatible with "two", two enabled, denied prompt
            (
                "one",
                [
                    ServiceWithDependencies(
                        name="one",
                        incompatible_with=[
                            ServiceWithReason(
                                name="two", reason=mock.MagicMock()
                            )
                        ],
                        depends_on=[],
                    )
                ],
                [EnabledService(name="two")],
                "one",
                "One",
                "",
                False,
                [False],
                [mock.call(msg=mock.ANY)],
                pytest.raises(exceptions.IncompatibleServiceStopsEnable),
            ),
            # incompatible with "two" and "three", three enabled, success
            (
                "one",
                [
                    ServiceWithDependencies(
                        name="one",
                        incompatible_with=[
                            ServiceWithReason(
                                name="two", reason=mock.MagicMock()
                            ),
                            ServiceWithReason(
                                name="three", reason=mock.MagicMock()
                            ),
                        ],
                        depends_on=[],
                    )
                ],
                [EnabledService(name="three")],
                "one",
                "One",
                "",
                False,
                [True],
                [mock.call(msg=mock.ANY)],
                does_not_raise(),
            ),
            # depends on "two", but two already enabled
            (
                "one",
                [
                    ServiceWithDependencies(
                        name="one",
                        incompatible_with=[],
                        depends_on=[
                            ServiceWithReason(
                                name="two", reason=mock.MagicMock()
                            )
                        ],
                    )
                ],
                [EnabledService(name="two")],
                "one",
                "One",
                "",
                False,
                [],
                [],
                does_not_raise(),
            ),
            # depends on "two", two not enabled, successful prompt
            (
                "one",
                [
                    ServiceWithDependencies(
                        name="one",
                        incompatible_with=[],
                        depends_on=[
                            ServiceWithReason(
                                name="two", reason=mock.MagicMock()
                            )
                        ],
                    )
                ],
                [],
                "one",
                "One",
                "",
                False,
                [True],
                [mock.call(msg=mock.ANY)],
                does_not_raise(),
            ),
            # depends on "two", two not enabled, denied prompt
            (
                "one",
                [
                    ServiceWithDependencies(
                        name="one",
                        incompatible_with=[],
                        depends_on=[
                            ServiceWithReason(
                                name="two", reason=mock.MagicMock()
                            )
                        ],
                    )
                ],
                [],
                "one",
                "One",
                "",
                False,
                [False],
                [mock.call(msg=mock.ANY)],
                pytest.raises(exceptions.RequiredServiceStopsEnable),
            ),
            # depends on "two" and "three", three not enabled, success prompt
            (
                "one",
                [
                    ServiceWithDependencies(
                        name="one",
                        incompatible_with=[],
                        depends_on=[
                            ServiceWithReason(
                                name="two", reason=mock.MagicMock()
                            ),
                            ServiceWithReason(
                                name="three", reason=mock.MagicMock()
                            ),
                        ],
                    )
                ],
                [EnabledService(name="two")],
                "one",
                "One",
                "",
                False,
                [True],
                [mock.call(msg=mock.ANY)],
                does_not_raise(),
            ),
            # a variant is enabled, second variant is being enabled
            (
                "two",
                [],
                [
                    EnabledService(
                        name="two", variant_enabled=True, variant_name="one"
                    )
                ],
                "two",
                "Two",
                "two",
                False,
                [False],
                [mock.call(msg=mock.ANY)],
                pytest.raises(exceptions.IncompatibleServiceStopsEnable),
            ),
            # lots of stuff
            (
                "one",
                [
                    ServiceWithDependencies(
                        name="one",
                        incompatible_with=[
                            ServiceWithReason(
                                name="two", reason=mock.MagicMock()
                            ),
                            ServiceWithReason(
                                name="three", reason=mock.MagicMock()
                            ),
                            ServiceWithReason(
                                name="four", reason=mock.MagicMock()
                            ),
                        ],
                        depends_on=[
                            ServiceWithReason(
                                name="five", reason=mock.MagicMock()
                            ),
                            ServiceWithReason(
                                name="six", reason=mock.MagicMock()
                            ),
                            ServiceWithReason(
                                name="seven", reason=mock.MagicMock()
                            ),
                        ],
                    )
                ],
                [
                    EnabledService(name="two"),
                    EnabledService(name="four"),
                    EnabledService(name="six"),
                ],
                "one",
                "One",
                "",
                False,
                [True, True, True, True],
                [
                    mock.call(msg=mock.ANY),
                    mock.call(msg=mock.ANY),
                    mock.call(msg=mock.ANY),
                    mock.call(msg=mock.ANY),
                ],
                does_not_raise(),
            ),
        ],
    )
    @mock.patch("uaclient.entitlements.get_title")
    @mock.patch("uaclient.util.prompt_for_confirmation")
    @mock.patch("uaclient.util.is_config_value_true")
    def test_prompt_for_dependency_handling(
        self,
        m_is_config_value_true,  # type: ignore
        m_prompt_for_confirmation,  # type: ignore
        m_entitlement_get_title,  # type: ignore
        service,  # type: ignore
        all_dependencies,  # type: ignore
        enabled_services,  # type: ignore
        called_name,  # type: ignore
        service_title,  # type: ignore
        variant,  # type: ignore
        cfg_block_disable_on_enable,  # type: ignore
        prompt_side_effects,  # type: ignore
        expected_prompts,  # type: ignore
        expected_raise,  # type: ignore
        FakeConfig,  # type: ignore
    ):
        m_entitlement_get_title.side_effect = (
            lambda cfg, name, variant=variant: name.title()  # type: ignore[misc]
        )
        m_is_config_value_true.return_value = cfg_block_disable_on_enable
        m_prompt_for_confirmation.side_effect = prompt_side_effects

        with expected_raise:
            prompt_for_dependency_handling(  # type: ignore[misc]
                FakeConfig(),  # type: ignore[misc]
                service,  # type: ignore[misc]
                all_dependencies,  # type: ignore[misc]
                enabled_services,  # type: ignore[misc]
                called_name,  # type: ignore[misc]
                variant,  # type: ignore[misc]
                service_title,  # type: ignore[misc]
            )

        assert expected_prompts == m_prompt_for_confirmation.call_args_list  # type: ignore[misc]
