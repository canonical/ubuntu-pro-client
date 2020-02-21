import pytest

from uaclient import config

try:
    from typing import Any, Dict, List  # noqa
except ImportError:
    # typing isn't available on trusty, so ignore its absence
    pass


def machine_token(
    entitlement_type: str,
    *,
    affordances: "Dict[str, Any]" = None,
    directives: "Dict[str, Any]" = None,
    entitled: bool = True,
    obligations: "Dict[str, Any]" = None,
    suites: "List[str]" = None
) -> "Dict[str, Any]":
    return {
        "resourceTokens": [
            {
                "type": entitlement_type,
                "token": "{}-token".format(entitlement_type),
            }
        ],
        "machineToken": "blah",
        "machineTokenInfo": {
            "contractInfo": {
                "resourceEntitlements": [
                    machine_access(
                        entitlement_type,
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
    entitlement_type: str,
    *,
    affordances: "Dict[str, Any]" = None,
    directives: "Dict[str, Any]" = None,
    entitled: bool = True,
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
            "aptURL": "http://{}".format(entitlement_type.upper()),
            "aptKey": "APTKEY",
            "suites": suites,
        }
    return {
        "obligations": obligations,
        "type": entitlement_type,
        "entitled": entitled,
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

    def factory_func(
        cls,
        *,
        affordances: "Dict[str, Any]" = None,
        directives: "Dict[str, Any]" = None,
        entitled: bool = True,
        suites: "List[str]" = None
    ):
        cfg = config.UAConfig(cfg={"data_dir": tmpdir.strpath})
        cfg.write_cache(
            "machine-token",
            machine_token(
                cls.name,
                affordances=affordances,
                directives=directives,
                entitled=entitled,
                suites=suites,
            ),
        )
        return cls(cfg)

    return factory_func
