import os

from behave import given


def _state_dir():
    return os.environ["UACLIENT_BEHAVE_RETRY_STATE_DIR"]


def _marker_path(key):
    return os.path.join(_state_dir(), key)


@given("the step passes")
def step_passes(context):
    del context


@given("the step always fails")
def step_always_fails(context):
    del context
    raise AssertionError("intentional persistent failure")


@given('the step fails once for key "{key}"')
def step_fails_once(context, key):
    del context
    marker_path = _marker_path(key)
    if os.path.exists(marker_path):
        return

    with open(marker_path, "w") as stream:
        stream.write("failed once\n")

    raise AssertionError("intentional first-run failure")
