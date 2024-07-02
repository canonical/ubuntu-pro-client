from argparse import Namespace

import mock
import pytest

from uaclient import exceptions, messages
from uaclient.api.u.pro.services.dependencies.v1 import (
    DependenciesResult,
    ServiceWithDependencies,
    ServiceWithReason,
)
from uaclient.api.u.pro.services.enable.v1 import EnableOptions, EnableResult
from uaclient.api.u.pro.status.enabled_services.v1 import (
    EnabledService,
    EnabledServicesResult,
)
from uaclient.api.u.pro.status.is_attached.v1 import IsAttachedResult
from uaclient.cli.enable import (
    _enable_landscape,
    _enable_one_service,
    _EnableOneServiceResult,
    _print_json_output,
    enable_command,
    prompt_for_dependency_handling,
)
from uaclient.testing.helpers import does_not_raise


class TestActionEnable:
    @pytest.mark.parametrize(
        [
            "is_attached",
            "args",
            "kwargs",
            "refresh_side_effect",
            "valid_entitlement_names",
            "enabled_services",
            "dependencies",
            "entitlements_for_enabling",
            "enable_one_service_side_effect",
            "expected_enable_one_service_calls",
            "expected_print_json_output_calls",
            "expected_raises",
        ],
        (
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
                ),
                {},
                None,
                (["one", "two", "three"], []),
                EnabledServicesResult(enabled_services=[]),
                DependenciesResult(services=mock.sentinel.dependencies),
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
                        mock.sentinel.dependencies,
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
                ),
                {},
                None,
                (["two"], ["one", "three"]),
                EnabledServicesResult(enabled_services=[]),
                DependenciesResult(services=mock.sentinel.dependencies),
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
                ),
                {},
                None,
                (["one", "two"], ["three"]),
                EnabledServicesResult(enabled_services=[]),
                DependenciesResult(services=mock.sentinel.dependencies),
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
        m_is_attached,
        m_we_are_currently_root,
        m_create_interactive_only_print_function,
        m_refresh,
        m_print_json_output,
        m_get_valid_entitlement_names,
        m_enabled_services,
        m_dependencies,
        m_order_entitlements_for_enabling,
        m_enable_one_service,
        m_update_activity_token,
        is_attached,
        args,
        kwargs,
        refresh_side_effect,
        valid_entitlement_names,
        enabled_services,
        dependencies,
        entitlements_for_enabling,
        enable_one_service_side_effect,
        expected_enable_one_service_calls,
        expected_print_json_output_calls,
        expected_raises,
        FakeConfig,
        fake_machine_token_file,
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
            enable_command.action(args, cfg=FakeConfig(), **kwargs)

        assert (
            expected_enable_one_service_calls
            == m_enable_one_service.call_args_list
        )
        assert (
            expected_print_json_output_calls
            == m_print_json_output.call_args_list
        )

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
                        "message": messages.ALREADY_ENABLED.format(
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
                    "access_only": mock.sentinel.access_only,
                    "assume_yes": mock.sentinel.assume_yes,
                    "json_output": False,
                    "extra_args": mock.sentinel.extra_args,
                    "enabled_services": [],
                    "all_dependencies": [],
                },
                None,
                EnableResult(
                    enabled=["landscape"],
                    disabled=[],
                    reboot_required=mock.sentinel.reboot,
                    messages=[],
                ),
                None,
                [],
                [
                    mock.call(
                        mock.ANY,
                        mock.sentinel.access_only,
                        extra_args=mock.sentinel.extra_args,
                        progress_object=mock.sentinel.cli_progress,
                    )
                ],
                [],
                [mock.call(cfg=mock.ANY)],
                _EnableOneServiceResult(
                    success=True, needs_reboot=mock.sentinel.reboot, error=None
                ),
            ),
            # non-landscape
            (
                {
                    "ent_name": "one",
                    "variant": mock.sentinel.variant,
                    "access_only": mock.sentinel.access_only,
                    "assume_yes": mock.sentinel.assume_yes,
                    "json_output": False,
                    "extra_args": mock.sentinel.extra_args,
                    "enabled_services": [],
                    "all_dependencies": [],
                },
                None,
                None,
                EnableResult(
                    enabled=["one"],
                    disabled=[],
                    reboot_required=mock.sentinel.reboot,
                    messages=[],
                ),
                [],
                [],
                [
                    mock.call(
                        EnableOptions(
                            service="one",
                            variant=mock.sentinel.variant,
                            access_only=mock.sentinel.access_only,
                        ),
                        mock.ANY,
                        progress_object=mock.sentinel.cli_progress,
                    )
                ],
                [mock.call(cfg=mock.ANY)],
                _EnableOneServiceResult(
                    success=True, needs_reboot=mock.sentinel.reboot, error=None
                ),
            ),
            # json output
            (
                {
                    "ent_name": "one",
                    "variant": mock.sentinel.variant,
                    "access_only": mock.sentinel.access_only,
                    "assume_yes": mock.sentinel.assume_yes,
                    "json_output": True,
                    "extra_args": mock.sentinel.extra_args,
                    "enabled_services": [],
                    "all_dependencies": [],
                },
                None,
                None,
                EnableResult(
                    enabled=["one"],
                    disabled=[],
                    reboot_required=mock.sentinel.reboot,
                    messages=[],
                ),
                [],
                [],
                [
                    mock.call(
                        EnableOptions(
                            service="one",
                            variant=mock.sentinel.variant,
                            access_only=mock.sentinel.access_only,
                        ),
                        mock.ANY,
                        progress_object=None,
                    )
                ],
                [mock.call(cfg=mock.ANY)],
                _EnableOneServiceResult(
                    success=True, needs_reboot=mock.sentinel.reboot, error=None
                ),
            ),
        ),
    )
    @mock.patch("uaclient.cli.status.status")
    @mock.patch("uaclient.cli.enable._enable")
    @mock.patch("uaclient.cli.enable._enable_landscape")
    @mock.patch("uaclient.cli.enable.cli_util.CLIEnableDisableProgress")
    @mock.patch("uaclient.cli.enable.prompt_for_dependency_handling")
    @mock.patch("uaclient.cli.enable.entitlements.entitlement_factory")
    @mock.patch("uaclient.cli.cli_util.create_interactive_only_print_function")
    def test_enable_one_service(
        self,
        m_create_interactive_only_print_function,
        m_entitlement_factory,
        m_prompt_for_dependency_handling,
        m_progress_class,
        m_enable_landscape,
        m_enable,
        m_status,
        kwargs,
        prompt_for_dependency_handling_side_effect,
        enable_landscape_result,
        enable_result,
        expected_prompt_for_dependency_handling_calls,
        expected_enable_landscape_calls,
        expected_enable_calls,
        expected_status_calls,
        expected_result,
        FakeConfig,
    ):
        mock_ent = mock.MagicMock()
        m_entitlement_factory.return_value = mock_ent
        mock_ent.name = kwargs.get("ent_name")
        mock_ent.title = mock.sentinel.ent_title
        m_prompt_for_dependency_handling.side_effect = (
            prompt_for_dependency_handling_side_effect
        )
        m_progress_class.return_value = mock.sentinel.cli_progress
        m_enable_landscape.return_value = enable_landscape_result
        m_enable.return_value = enable_result

        assert expected_result == _enable_one_service(FakeConfig(), **kwargs)

        assert (
            expected_prompt_for_dependency_handling_calls
            == m_prompt_for_dependency_handling.call_args_list
        )
        assert (
            expected_enable_landscape_calls
            == m_enable_landscape.call_args_list
        )
        assert expected_enable_calls == m_enable.call_args_list
        assert expected_status_calls == m_status.call_args_list

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
        m_landscape_entitlement,
        m_lock,
        enable_side_effect,
        expected_raises,
        expected_result,
        FakeConfig,
    ):
        m_enable = m_landscape_entitlement.return_value.enable
        m_enable.side_effect = enable_side_effect
        with expected_raises:
            assert expected_result == _enable_landscape(
                FakeConfig,
                mock.sentinel.access_only,
                mock.sentinel.extra_args,
                None,
            )
        assert [
            mock.call(
                mock.ANY,
                called_name="landscape",
                access_only=mock.sentinel.access_only,
                extra_args=mock.sentinel.extra_args,
            )
        ] == m_landscape_entitlement.call_args_list

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
        self, m_print, json_output, expected_print_calls
    ):
        _print_json_output(json_output, {}, [], [], [], [], True)
        assert expected_print_calls == m_print.call_args_list


class TestPromptForDependencyHandling:
    @pytest.mark.parametrize(
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
        [
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
        m_is_config_value_true,
        m_prompt_for_confirmation,
        m_entitlement_get_title,
        service,
        all_dependencies,
        enabled_services,
        called_name,
        service_title,
        variant,
        cfg_block_disable_on_enable,
        prompt_side_effects,
        expected_prompts,
        expected_raise,
        FakeConfig,
    ):
        m_entitlement_get_title.side_effect = (
            lambda cfg, name, variant=variant: name.title()
        )
        m_is_config_value_true.return_value = cfg_block_disable_on_enable
        m_prompt_for_confirmation.side_effect = prompt_side_effects

        with expected_raise:
            prompt_for_dependency_handling(
                FakeConfig(),
                service,
                all_dependencies,
                enabled_services,
                called_name,
                variant,
                service_title,
            )

        assert expected_prompts == m_prompt_for_confirmation.call_args_list
