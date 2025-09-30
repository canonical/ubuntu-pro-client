#!/usr/bin/env python3
"""
Demo script to test the auto-enable JSON output functionality.

This script simulates the pro enable --auto --format=json --assume-yes command
to demonstrate that the bug has been fixed and JSON output is now properly
generated for auto-enable operations.
"""

import json
import sys
import tempfile
from argparse import Namespace
from unittest.mock import Mock, patch

# Add the uaclient package to path for imports
sys.path.insert(0, '/home/balaraj/ubuntu-pro-client')

from uaclient.cli.enable import enable_command
from uaclient.config import UAConfig
from uaclient.api.u.pro.status.is_attached.v1 import IsAttachedResult
from uaclient.api.u.pro.services.dependencies.v1 import DependenciesResult
from uaclient.api.u.pro.status.enabled_services.v1 import EnabledServicesResult
from uaclient.cli.enable import _EnableOneServiceResult  # type: ignore[misc]


def demo_auto_enable_json():
    """Demo the fixed auto-enable JSON output functionality."""
    print("=" * 60)
    print("Demo: pro enable --auto --format=json --assume-yes")
    print("=" * 60)
    
    # Create a temporary directory for the fake config
    with tempfile.TemporaryDirectory() as tmpdir:
        # Mock all the dependencies
        with patch('uaclient.cli.enable._is_attached') as m_is_attached, \
             patch('uaclient.util.we_are_currently_root', return_value=True), \
             patch('uaclient.cli.cli_util.create_interactive_only_print_function') as m_print_func, \
             patch('uaclient.contract.refresh'), \
             patch('uaclient.cli.enable.contract.get_enabled_by_default_services') as m_get_services, \
             patch('uaclient.cli.enable._enabled_services') as m_enabled_services, \
             patch('uaclient.cli.enable._dependencies') as m_dependencies, \
             patch('uaclient.cli.enable._enable_one_service') as m_enable_one, \
             patch('uaclient.contract.UAContractClient.update_activity_token'), \
             patch('uaclient.files.machine_token.get_machine_token_file') as m_token_file:
            
            # Set up the mocks to simulate a successful auto-enable scenario
            m_is_attached.return_value = IsAttachedResult(
                is_attached=True,
                contract_status="active",
                contract_remaining_days=100,
                is_attached_and_contract_valid=True
            )
            
            # Mock the print function to capture output
            captured_output = []
            def capture_print(*args, **kwargs):  # type: ignore[misc]
                captured_output.append(' '.join(str(arg) for arg in args))  # type: ignore[misc]
            
            m_print_func.return_value = capture_print
            
            # Set up services to be auto-enabled
            service1 = Mock()
            service1.name = "esm-infra"
            service2 = Mock()
            service2.name = "livepatch"
            
            m_get_services.return_value = [service1, service2]
            
            # Mock machine token file
            mock_token_file = Mock()
            mock_token_file.entitlements.return_value = {"some": "entitlements"}
            m_token_file.return_value = mock_token_file
            
            # Mock enabled services and dependencies
            m_enabled_services.return_value = EnabledServicesResult(enabled_services=[])
            m_dependencies.return_value = DependenciesResult(services=[])
            
            # Mock successful enable operations
            m_enable_one.side_effect = [
                _EnableOneServiceResult(success=True, needs_reboot=False, error=None),
                _EnableOneServiceResult(success=True, needs_reboot=True, error=None),
            ]
            
            # Create config and args as they would be in the real CLI
            config = UAConfig({"data_dir": tmpdir})
            args = Namespace(
                service=[],
                format="json",
                variant="",
                access_only=False,
                assume_yes=True,
                auto=True
            )
            
            # Capture stdout to see the JSON output
            from io import StringIO
            old_stdout = sys.stdout
            sys.stdout = captured_stdout = StringIO()
            
            try:
                # Execute the enable command
                result = enable_command.action(args, cfg=config)  # type: ignore[misc]
                
                # Get the captured JSON output
                json_output = captured_stdout.getvalue().strip()
                
                print("Command exit code:", result)  # type: ignore[misc]
                print("\nJSON Output:")
                print(json_output)
                
                if json_output:
                    try:
                        # Parse and pretty-print the JSON
                        json_data = json.loads(json_output)
                        print("\nParsed JSON (pretty-printed):")
                        print(json.dumps(json_data, indent=2))
                        
                        # Verify expected structure
                        print("\nValidation:")
                        assert json_data.get("result") == "success", "Expected success result"
                        assert len(json_data.get("processed_services", [])) == 2, "Expected 2 processed services"
                        assert "esm-infra" in json_data["processed_services"], "Expected esm-infra to be processed"
                        assert "livepatch" in json_data["processed_services"], "Expected livepatch to be processed"
                        assert json_data.get("needs_reboot") == True, "Expected reboot to be needed"
                        print("✓ All validations passed!")
                        
                    except json.JSONDecodeError as e:
                        print(f"❌ Failed to parse JSON: {e}")
                        return False
                else:
                    print("❌ No JSON output captured!")
                    return False
                    
            finally:
                sys.stdout = old_stdout
                
    print("\n" + "=" * 60)
    print("Demo completed successfully! 🎉")
    print("The bug has been fixed - pro enable --auto now produces JSON output.")
    print("=" * 60)
    return True


if __name__ == "__main__":
    try:
        demo_auto_enable_json()
    except Exception as e:
        print(f"Demo failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)