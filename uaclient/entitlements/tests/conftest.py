from typing import Any, Dict, List, Optional

import pytest

from uaclient import config, event_logger


def machine_token(
    entitlement_type: str,
    *,
    affordances: Dict[str, Any] = None,
    directives: Dict[str, Any] = None,
    overrides: List[Dict[str, Any]] = None,
    entitled: bool = True,
    obligations: Dict[str, Any] = None,
    suites: List[str] = None,
    additional_packages: List[str] = None
) -> Dict[str, Any]:
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
                        overrides=overrides,
                        entitled=entitled,
                        obligations=obligations,
                        suites=suites,
                        additional_packages=additional_packages,
                    )
                ]
            }
        },
    }


def machine_access(
    entitlement_type: str,
    *,
    affordances: Dict[str, Any] = None,
    directives: Dict[str, Any] = None,
    overrides: List[Dict[str, Any]] = None,
    entitled: bool = True,
    obligations: Dict[str, Any] = None,
    suites: List[str] = None,
    additional_packages: List[str] = None
) -> Dict[str, Any]:
    if affordances is None:
        affordances = {}
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

        if additional_packages:
            directives["additionalPackages"] = additional_packages
    if overrides is None:
        overrides = []

    return {
        "obligations": obligations,
        "type": entitlement_type,
        "entitled": entitled,
        "directives": directives,
        "affordances": affordances,
        "overrides": overrides,
    }


@pytest.fixture
def entitlement_factory(tmpdir, FakeConfig, get_fake_machine_token_file):
    """
    A pytest fixture that returns a function that instantiates an entitlement

    The function requires an entitlement class as its first argument, and takes
    keyword arguments for affordances, directives and suites which, if given,
    replace the default values in the resourceEntitlements of the
    machine-token.json file for the entitlement.
    """

    def factory_func(
        cls,
        *,
        affordances: Dict[str, Any] = None,
        directives: Dict[str, Any] = None,
        obligations: Dict[str, Any] = None,
        overrides: List[Dict[str, Any]] = None,
        entitled: bool = True,
        allow_beta: bool = False,
        called_name: str = "",
        access_only: bool = False,
        purge: bool = False,
        assume_yes: Optional[bool] = None,
        suites: List[str] = None,
        additional_packages: List[str] = None,
        cfg: Optional[config.UAConfig] = None,
        cfg_extension: Optional[Dict[str, Any]] = None,
        cfg_features: Optional[Dict[str, Any]] = None,
        # Those extra args should be used for scenarios where a cls
        # instance requires something that is not shared between all
        # entitlement classes
        extra_args: Optional[Dict[str, Any]] = None
    ):
        if not cfg:
            cfg_arg = {"data_dir": tmpdir.strpath}
            if cfg_extension is not None:
                cfg_arg.update(cfg_extension)
            if cfg_features is not None:
                cfg_arg["features"] = cfg_features
            cfg = FakeConfig(cfg_overrides=cfg_arg)
            machine_token_file = get_fake_machine_token_file
            machine_token_file.attached = True
            machine_token_file.token = (
                machine_token(
                    cls.name,
                    affordances=affordances,
                    directives=directives,
                    overrides=overrides,
                    obligations=obligations,
                    entitled=entitled,
                    suites=suites,
                    additional_packages=additional_packages,
                ),
            )

        args = {
            "allow_beta": allow_beta,
            "called_name": called_name,
            "access_only": access_only,
            "purge": purge,
        }
        if assume_yes is not None:
            args["assume_yes"] = assume_yes

        if extra_args:
            args = {**args, **extra_args}

        return cls(machine_token_file, cfg, **args)

    return factory_func


@pytest.fixture
def event():
    event = event_logger.get_event_logger()
    event.reset()

    return event
