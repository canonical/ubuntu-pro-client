"""Tests related to uaclient.entitlement.base module."""

from functools import partial

import pytest

from uaclient import messages
from uaclient.entitlements.cis import CISEntitlement


@pytest.fixture
def cis_entitlement(entitlement_factory):
    return partial(
        entitlement_factory,
        CISEntitlement,
    )


class TestCISEntitlement:
    @pytest.mark.parametrize(
        "called_name,expected",
        (
            (
                "cis",
                {
                    "post_enable": [messages.CIS_POST_ENABLE],
                },
            ),
            (
                "usg",
                {
                    "post_enable": [messages.CIS_USG_POST_ENABLE],
                },
            ),
        ),
    )
    def test_messages(self, called_name, expected, cis_entitlement):
        entitlement = cis_entitlement(
            called_name=called_name,
        )

        assert expected == entitlement.messaging

    @pytest.mark.parametrize(
        "called_name,expected",
        (
            ("cis", ["test-package"]),
            ("usg", []),
        ),
    )
    def test_packages(self, called_name, expected, cis_entitlement):
        entitlement = cis_entitlement(
            called_name=called_name,
            directives={
                "additionalPackages": ["test-package"],
            },
        )

        assert expected == entitlement.packages

    @pytest.mark.parametrize(
        "called_name,expected",
        (
            ("cis", messages.CIS_TITLE),
            ("usg", messages.CIS_USG_TITLE),
        ),
    )
    def test_title(self, called_name, expected, cis_entitlement):
        entitlement = cis_entitlement(
            called_name=called_name,
        )

        assert expected == entitlement.title
