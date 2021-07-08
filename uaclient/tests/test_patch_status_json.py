import logging
import pytest

import json

from lib.patch_status_json import patch_status_json_schema_0_1

UNATTACHED_UNPATCHED_STATUS = {
    "_doc": "Content provided in json response is currently considered ...",
    "attached": False,
    "expires": "n/a",
    "techSupportLevel": "n/a",
    "notices": [],
    "services": [
        {
            "name": "cc-eal",
            "available": "yes",
            "description": "Common Criteria EAL2 Provisioning Packages",
        }
    ],
    "origin": None,
    "configStatusDetails": "No Ubuntu Advantage operations are running",
    "configStatus": "inactive",
}

# Note that (UN)ATTACHED_PATCHED_STATUS is only a capture of expected minimal
# schema transformation performed by patch_status function to allow ua status
# to work without errors for non-root user. It is not expected to be a full
# representation of schema which will be written once a root user runs any
# ua command which will rewrite the full latest schema to status.json.
UNATTACHED_PATCHED_STATUS = {
    "execution_details": "No Ubuntu Advantage operations are running",
    "_schema_version": "0.1",
    "origin": None,
    "account": {"name": "", "id": ""},
    "expires": "n/a",
    "notices": [],
    "services": [
        {
            "available": "yes",
            "name": "cc-eal",
            "description": "Common Criteria EAL2 Provisioning Packages",
        }
    ],
    "attached": False,
    "execution_status": "inactive",
    "contract": {"name": "", "id": "", "tech_support_level": "n/a"},
    "_doc": "Content provided in json response is currently considered ...",
}

ATTACHED_UNPATCHED_STATUS = {
    "_doc": "Content provided in json response is currently considered ...",
    "configStatusDetails": "Operation in progress: ua attach (pid:33140)",
    "configStatus": "active",
    "subscription": "chad.smith@canonical.com",
    "subscription-id": "cAKuvrqHend2ZHxUYTyJqXhULJ-4r2lpCzd1HLC_lrJg",
    "services": [
        {
            "entitled": "yes",
            "description": "Common Criteria EAL2 Provisioning Packages",
            "description_override": None,
            "name": "cc-eal",
            "statusDetails": "CC EAL2 is not configured",
            "status": "disabled",
        }
    ],
    "notices": [["Operation in progress: ua attach"]],
    "attached": True,
    "account-id": "aAHQlZdfWiafnWvjDZCZDqZzDUComc8WF7IJnoG6GAmA",
    "account": "chad.smith@canonical.com",
    "techSupportLevel": "n/a",
    "expires": "9999-12-31T00:00:00",
    "origin": "free",
}

ATTACHED_PATCHED_STATUS = {
    "_doc": "Content provided in json response is currently considered ...",
    "origin": "free",
    "execution_details": "Operation in progress: ua attach (pid:33140)",
    "execution_status": "active",
    "expires": "9999-12-31T00:00:00+00:00",
    "contract": {
        "tech_support_level": "n/a",
        "name": "chad.smith@canonical.com",
        "id": "cAKuvrqHend2ZHxUYTyJqXhULJ-4r2lpCzd1HLC_lrJg",
    },
    "services": [
        {
            "description_override": None,
            "entitled": "yes",
            "description": "Common Criteria EAL2 Provisioning Packages",
            "status": "disabled",
            "statusDetails": "CC EAL2 is not configured",
            "name": "cc-eal",
        }
    ],
    "_schema_version": "0.1",
    "attached": True,
    "notices": [["Operation in progress: ua attach"]],
    "account": {
        "name": "chad.smith@canonical.com",
        "id": "aAHQlZdfWiafnWvjDZCZDqZzDUComc8WF7IJnoG6GAmA",
    },
}


@pytest.mark.parametrize("caplog_text", [logging.DEBUG], indirect=True)
class TestPatchStatusJSONSchema0_1:
    @pytest.mark.parametrize(
        "orig_status,expected_status,expected_logs",
        (
            (
                UNATTACHED_UNPATCHED_STATUS,
                UNATTACHED_PATCHED_STATUS,
                ["Patching /var/lib/ubuntu-advantage/status.json schema"],
            ),
            (
                ATTACHED_UNPATCHED_STATUS,
                ATTACHED_PATCHED_STATUS,
                ["Patching /var/lib/ubuntu-advantage/status.json schema"],
            ),
            (UNATTACHED_PATCHED_STATUS, UNATTACHED_PATCHED_STATUS, []),
        ),
    )
    def test_unattached_noops(
        self, orig_status, expected_status, expected_logs, tmpdir, caplog_text
    ):
        status_file = tmpdir.join("status.json")
        status_file.write(json.dumps(orig_status))
        patch_status_json_schema_0_1(status_file=status_file.strpath)
        assert expected_status == json.loads(status_file.read())
        debug_logs = caplog_text()
        for log in expected_logs:
            assert log in debug_logs
        if not expected_logs:
            assert (
                "Patching /var/lib/ubuntu-advantage/status.json"
                not in debug_logs
            )
