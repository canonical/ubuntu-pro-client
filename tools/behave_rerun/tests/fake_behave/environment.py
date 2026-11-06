import os
import sys


def _first_time(key):
    """Return True the first time it is called for key in this test."""
    marker = os.path.join(os.environ["UACLIENT_BEHAVE_RETRY_STATE_DIR"], key)
    if os.path.exists(marker):
        return False
    with open(marker, "w") as stream:
        stream.write("seen\n")
    return True


def before_feature(context, feature):
    if "before_feature_fails_once" in feature.tags and _first_time(
        "before_feature"
    ):
        raise RuntimeError("intentional before_feature failure")


def before_scenario(context, scenario):
    if "aborts_once" in scenario.tags and _first_time("abort"):
        sys.exit("intentional abort")
