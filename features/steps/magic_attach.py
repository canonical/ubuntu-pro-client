import json

from behave import when

from features.steps.shell import when_i_run_command
from uaclient.util import DatetimeAwareJSONDecoder


@when("I initiate the magic attach flow")
def when_i_initiate_magic_attach(context):
    when_i_run_command(
        context=context,
        command="pro api u.pro.attach.magic.initiate.v1",
        user_spec="as non-root",
    )

    magic_attach_resp = json.loads(
        context.process.stdout.strip(), cls=DatetimeAwareJSONDecoder
    )

    context.magic_token = magic_attach_resp["data"]["attributes"]["token"]


@when("I revoke the magic attach token")
def when_i_revoke_the_magic_attach_token(context):
    when_i_run_command(
        context=context,
        command="pro api u.pro.attach.magic.revoke.v1 --args magic_token={}".format(  # noqa
            context.magic_token
        ),
        user_spec="as non-root",
    )


@when("I wait for the magic attach token to be activated")
def when_i_wait_for_magic_attach_token(context):
    when_i_run_command(
        context=context,
        command="pro api u.pro.attach.magic.wait.v1 --args magic_token={}".format(  # noqa
            context.magic_token
        ),
        user_spec="as non-root",
    )
