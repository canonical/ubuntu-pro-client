# Ubuntu Pro Client: Auto-Enable JSON Output Fix

## Problem Statement

The `pro enable --auto --format=json --assume-yes` command was not producing any JSON output, violating the contract implied by the `--format=json` flag.

## Root Cause

The `_auto_enable_services` function was designed to perform auto-enable operations but did not collect results or emit JSON output. It had two main issues:

1. **Missing Result Aggregation**: The function performed enable operations in a loop but didn't collect the results for later reporting.
2. **Missing JSON Output**: The auto-enable path bypassed the JSON output generation that was available in the manual service enable path.

## Solution Implementation

### 1. Updated `_auto_enable_services` Function Signature

**Before:**
```python
def _auto_enable_services(
    cfg: config.UAConfig,
    variant: str,
    assume_yes: bool,
    json_output,
):
```

**After:**
```python
def _auto_enable_services(
    cfg: config.UAConfig,
    variant: str,
    assume_yes: bool,
    json_output,
    json_response: Dict[str, Any],
    processed_services: List[str],
    failed_services: List[str],
    errors: List[Dict[str, Any]],
    warnings: List[Dict[str, Any]],
) -> bool:
```

### 2. Added Result Collection Logic

**Before:**
```python
for enable_by_default_service in services_to_be_enabled:
    _enable_one_service(
        cfg=cfg,
        ent_name=enable_by_default_service.name,
        # ... other args
    )
```

**After:**
```python
success = True
needs_reboot = False

for enable_by_default_service in services_to_be_enabled:
    result = _enable_one_service(
        cfg=cfg,
        ent_name=enable_by_default_service.name,
        # ... other args
    )

    if result.success:
        processed_services.append(enable_by_default_service.name)
        if result.needs_reboot:
            needs_reboot = True
    else:
        success = False
        failed_services.append(enable_by_default_service.name)
        if result.error is not None:
            errors.append(result.error)

if needs_reboot:
    json_response["needs_reboot"] = True

return success
```

### 3. Updated Auto-Enable Call Site

**Before:**
```python
if auto:
    return _auto_enable_services(
        cfg=cfg,
        variant="",
        assume_yes=True,
        json_output=json_output,
    )
```

**After:**
```python
if auto:
    success = _auto_enable_services(
        cfg=cfg,
        variant="",
        assume_yes=True,
        json_output=json_output,
        json_response=json_response,
        processed_services=processed_services,
        failed_services=failed_services,
        errors=errors,
        warnings=warnings,
    )

    contract_client = contract.UAContractClient(cfg)
    contract_client.update_activity_token()

    _print_json_output(
        json_output,
        json_response,
        processed_services,
        failed_services,
        errors,
        warnings,
        success=success,
    )

    return 0 if success else 1
```

## Expected JSON Output Schema

The fix ensures that `pro enable --auto --format=json --assume-yes` now produces structured JSON output:

```json
{
  "_schema_version": "0.1",
  "result": "success",
  "processed_services": ["esm-infra", "livepatch"],
  "failed_services": [],
  "errors": [],
  "warnings": [],
  "needs_reboot": true
}
```

## Test Coverage

Added comprehensive test coverage for:
1. **Success scenario**: Multiple services enabled successfully, some requiring reboot
2. **Failure scenario**: Mixed success/failure results with proper error reporting  
3. **No services scenario**: When no services need to be auto-enabled

All tests validate that proper JSON is emitted and contains the expected structure and data.

## Manual Verification Steps

To verify the fix works:

1. Set up Ubuntu Pro client environment
2. Attach with `pro attach <token> --no-auto-enable`
3. Run `output=$(pro enable --auto --format=json --assume-yes)`
4. Verify `$output` contains valid JSON with service information
5. Confirm `echo "$output" | jq .` parses successfully

The fix ensures that automation scripts using the JSON output can now reliably determine which services were enabled and their status.