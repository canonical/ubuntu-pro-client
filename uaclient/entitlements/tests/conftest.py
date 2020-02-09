import pytest

from uaclient import config

try:
    from typing import Any, Dict, List, Optional  # noqa
except ImportError:
    # typing isn't available on trusty, so ignore its absence
    pass


def machine_token(
    type: str,
    *,
    affordances: "Dict[str, Any]" = None,
    directives: "Dict[str, Any]" = None,
    entitled: "Optional[bool]" = True,
    obligations: "Dict[str, Any]" = None,
    suites: "List[str]" = None
) -> "Dict[str, Any]":
    return {
        "resourceTokens": [{"Type": type, "Token": "%s-token" % type}],
        "machineToken": "blah",
        "machineTokenInfo": {
            "contractInfo": {
                "resourceEntitlements": [
                    machine_access(
                        type,
                        affordances=affordances,
                        directives=directives,
                        entitled=entitled,
                        obligations=obligations,
                        suites=suites,
                    )
                ]
            }
        },
    }


def machine_access(
    type: str,
    *,
    affordances: "Dict[str, Any]" = None,
    directives: "Dict[str, Any]" = None,
    entitled: "Optional[bool]" = True,
    obligations: "Dict[str, Any]" = None,
    suites: "List[str]" = None
) -> "Dict[str, Any]":
    if affordances is None:
        affordances = {"series": []}  # Will match all series
    if suites is None:
        suites = ["xenial"]
    if obligations is None:
        obligations = {"enableByDefault": True}
    if directives is None:
        directives = {
            "aptURL": "http://{}".format(type.upper()),
            "aptKey": "APTKEY",
            "suites": suites,
        }
    return {
        "obligations": obligations,
        "type": type,
        "entitled": True,
        "directives": directives,
        "affordances": affordances,
    }


@pytest.fixture
def entitlement_factory(tmpdir):
    """
    A pytest fixture that returns a function that instantiates an entitlement

    The function requires an entitlement class as its first argument, and takes
    keyword arguments for affordances, directives and suites which, if given,
    replace the default values in the machine-access-*.json file for the
    entitlement.
    """

    def factory_func(cls, *, affordances=None, directives=None, suites=None):
        cfg = config.UAConfig(cfg={"data_dir": tmpdir.strpath})
        cfg.write_cache(
            "machine-token",
            machine_token(
                cls.name,
                affordances=affordances,
                directives=directives,
                suites=suites,
            ),
        )
        return cls(cfg)

    return factory_func
