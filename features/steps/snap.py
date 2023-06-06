import json

from behave import then
from hamcrest import assert_that, equal_to

from features.steps.shell import when_i_run_command


def _get_snap_data(context, snap):
    cmd = (
        "curl -sS --unix-socket /run/snapd.socket http://localhost/v2/snaps/{}"
    )
    when_i_run_command(
        context,
        cmd.format(snap),
        "with sudo",
    )


@then("I check that snap `{snap}` is installed")
def i_check_that_snap_is_installed(context, snap):
    _get_snap_data(context, snap)
    snap_data_json = json.loads(context.process.stdout.strip())
    assert_that(snap_data_json["status-code"], equal_to(200))


@then("I check that snap `{snap}` is not installed")
def i_check_that_snap_is_not_installed(context, snap):
    _get_snap_data(context, snap)
    snap_data_json = json.loads(context.process.stdout.strip())
    assert_that(snap_data_json["status-code"], equal_to(404))
