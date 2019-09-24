"""Tests related to uaclient.entitlement.base module."""
import mock

import pytest

from uaclient import config
from uaclient.entitlements import base
from uaclient import status
from uaclient import util
from uaclient.status import ContractStatus

try:
    from typing import Tuple  # noqa
except ImportError:
    pass


class ConcreteTestEntitlement(base.UAEntitlement):

    name = "testconcreteentitlement"
    title = "Test Concrete Entitlement"
    description = "Entitlement for testing"

    def __init__(
        self,
        cfg=None,
        disable=None,
        enable=None,
        applicability_status=None,
        application_status=None,
    ):
        super().__init__(cfg)
        self._disable = disable
        self._enable = enable
        self._applicability_status = applicability_status
        self._application_status = application_status

    def disable(self):
        self._application_status = (
            status.ApplicationStatus.DISABLED,
            "disable() called",
        )
        return self._disable

    def enable(self, silent_if_inapplicable: bool = False):
        return self._enable

    def applicability_status(self):
        return self._applicability_status

    def application_status(self):
        return self._application_status


@pytest.fixture
def concrete_entitlement_factory(tmpdir):
    def factory(
        *,
        entitled: bool,
        applicability_status: "Tuple[status.ApplicabilityStatus, str]" = None,
        application_status: "Tuple[status.ApplicationStatus, str]" = None
    ) -> ConcreteTestEntitlement:
        cfg = config.UAConfig(cfg={"data_dir": tmpdir.strpath})
        machineToken = {
            "machineToken": "blah",
            "machineTokenInfo": {
                "contractInfo": {
                    "resourceEntitlements": [
                        {
                            "type": "testconcreteentitlement",
                            "entitled": entitled,
                        }
                    ]
                }
            },
        }
        cfg.write_cache("machine-token", machineToken)
        cfg.write_cache(
            "machine-access-testconcreteentitlement",
            {"entitlement": {"entitled": entitled}},
        )
        return ConcreteTestEntitlement(
            cfg,
            applicability_status=applicability_status,
            application_status=application_status,
        )

    return factory


class TestUaEntitlement:
    def test_entitlement_abstract_class(self):
        """UAEntitlement is abstract requiring concrete methods."""
        with pytest.raises(TypeError) as excinfo:
            base.UAEntitlement()
        expected_msg = (
            "Can't instantiate abstract class UAEntitlement with abstract"
            " methods application_status, description, disable, enable, name,"
            " title"
        )
        assert expected_msg == str(excinfo.value)

    def test_init_default_sets_up_uaconfig(self):
        """UAEntitlement sets up a uaconfig instance upon init."""
        entitlement = ConcreteTestEntitlement()
        assert "/var/lib/ubuntu-advantage" == entitlement.cfg.data_dir

    def test_init_accepts_a_uaconfig(self):
        """An instance of UAConfig can be passed to UAEntitlement."""
        cfg = config.UAConfig(cfg={"data_dir": "/some/path"})
        entitlement = ConcreteTestEntitlement(cfg)
        assert "/some/path" == entitlement.cfg.data_dir

    def test_can_disable_false_on_entitlement_inactive(
        self, capsys, concrete_entitlement_factory
    ):
        """When  status is INACTIVE, can_disable returns False."""
        entitlement = concrete_entitlement_factory(
            entitled=True,
            application_status=(status.ApplicationStatus.DISABLED, ""),
        )

        assert not entitlement.can_disable()

        expected_stdout = (
            "Test Concrete Entitlement is not currently enabled.\n"
            "See: sudo ua status\n"
        )
        stdout, _ = capsys.readouterr()
        assert expected_stdout == stdout

    def test_can_disable_true_on_entitlement_active(
        self, capsys, concrete_entitlement_factory
    ):
        """When entitlement is ENABLED, can_disable returns True."""
        entitlement = concrete_entitlement_factory(
            entitled=True,
            application_status=(status.ApplicationStatus.ENABLED, ""),
        )

        assert entitlement.can_disable()

        stdout, _ = capsys.readouterr()
        assert "" == stdout

    @pytest.mark.parametrize("silent", (True, False, None))
    def test_can_enable_false_on_unentitled(
        self, capsys, concrete_entitlement_factory, silent
    ):
        """When entitlement contract is not enabled, can_enable is False."""

        entitlement = concrete_entitlement_factory(entitled=False)

        kwargs = {}
        if silent is not None:
            kwargs["silent"] = silent
        assert not entitlement.can_enable(**kwargs)

        expected_stdout = (
            "This subscription is not entitled to Test Concrete Entitlement.\n"
            "See: sudo ua status or https://ubuntu.com/advantage\n"
        )
        if silent:
            expected_stdout = ""
        stdout, _ = capsys.readouterr()
        assert expected_stdout == stdout

    @pytest.mark.parametrize("silent", (True, False, None))
    def test_can_enable_false_on_entitlement_active(
        self, capsys, concrete_entitlement_factory, silent
    ):
        """When entitlement is ENABLED, can_enable returns False."""
        application_status = status.ApplicationStatus.ENABLED
        entitlement = concrete_entitlement_factory(
            entitled=True, application_status=(application_status, "")
        )

        kwargs = {}
        if silent is not None:
            kwargs["silent"] = silent
        assert not entitlement.can_enable(**kwargs)

        expected_stdout = (
            "Test Concrete Entitlement is already enabled.\n"
            "See: sudo ua status\n"
        )
        if silent:
            expected_stdout = ""
        stdout, _ = capsys.readouterr()
        assert expected_stdout == stdout

    @pytest.mark.parametrize("silent", (True, False, None))
    def test_can_enable_false_on_entitlement_inapplicable(
        self, capsys, concrete_entitlement_factory, silent
    ):
        """When entitlement is INAPPLICABLE, can_enable returns False."""
        entitlement = concrete_entitlement_factory(
            entitled=True,
            applicability_status=(
                status.ApplicabilityStatus.INAPPLICABLE,
                "msg",
            ),
            application_status=(status.ApplicationStatus.DISABLED, ""),
        )

        kwargs = {}
        if silent is not None:
            kwargs["silent"] = silent
        assert not entitlement.can_enable(**kwargs)

        expected_stdout = "msg\n"
        if silent:
            expected_stdout = ""
        stdout, _ = capsys.readouterr()
        assert expected_stdout == stdout

    @pytest.mark.parametrize("silent", (True, False, None))
    def test_can_enable_true_on_entitlement_inactive(
        self, capsys, concrete_entitlement_factory, silent
    ):
        """When an entitlement is applicable and disabled, we can_enable"""
        entitlement = concrete_entitlement_factory(
            entitled=True,
            applicability_status=(status.ApplicabilityStatus.APPLICABLE, ""),
            application_status=(status.ApplicationStatus.DISABLED, ""),
        )

        kwargs = {}
        if silent is not None:
            kwargs["silent"] = silent
        assert entitlement.can_enable(**kwargs)

        stdout, _ = capsys.readouterr()
        assert "" == stdout

    def test_contract_status_entitled(self, concrete_entitlement_factory):
        """The contract_status returns ENTITLED when entitlement enabled."""
        entitlement = concrete_entitlement_factory(entitled=True)
        assert ContractStatus.ENTITLED == entitlement.contract_status()

    def test_contract_status_unentitled(self, concrete_entitlement_factory):
        """The contract_status returns NONE when entitlement is unentitled."""
        entitlement = concrete_entitlement_factory(entitled=False)
        assert ContractStatus.UNENTITLED == entitlement.contract_status()

    @pytest.mark.parametrize(
        "orig_access,delta",
        (({}, {}), ({}, {"entitlement": {"entitled": False}})),
    )
    def test_process_contract_deltas_does_nothing_on_empty_orig_access(
        self, concrete_entitlement_factory, orig_access, delta
    ):
        """When orig_acccess dict is empty perform no work."""
        entitlement = concrete_entitlement_factory(
            entitled=True,
            applicability_status=(status.ApplicabilityStatus.APPLICABLE, ""),
            application_status=(status.ApplicationStatus.DISABLED, ""),
        )
        expected = {"entitlement": {"entitled": True}}
        assert expected == entitlement.cfg.read_cache(
            "machine-access-testconcreteentitlement"
        )
        entitlement.process_contract_deltas(orig_access, delta)
        # Cache was not cleaned
        assert expected == entitlement.cfg.read_cache(
            "machine-access-testconcreteentitlement"
        )

    @pytest.mark.parametrize(
        "orig_access,delta",
        (
            ({"entitlement": {"entitled": True}}, {}),  # no deltas
            (
                {"entitlement": {"entitled": False}},
                {"entitlement": {"entitled": True}},
            ),  # transition to entitled
            (
                {"entitlement": {"entitled": False}},
                {
                    "entitlement": {
                        "entitled": False,  # overridden True by series trusty
                        "series": {"trusty": {"entitled": True}},
                    }
                },
            ),
        ),
    )
    @mock.patch(
        "uaclient.util.get_platform_info", return_value={"series": "trusty"}
    )
    def test_process_contract_deltas_does_nothing_when_delta_remains_entitled(
        self, m_platform_info, concrete_entitlement_factory, orig_access, delta
    ):
        """If deltas do not represent transition to unentitled, do nothing."""
        entitlement = concrete_entitlement_factory(
            entitled=True,
            applicability_status=(status.ApplicabilityStatus.APPLICABLE, ""),
            application_status=(status.ApplicationStatus.DISABLED, ""),
        )
        expected = {"entitlement": {"entitled": True}}
        assert expected == entitlement.cfg.read_cache(
            "machine-access-testconcreteentitlement"
        )
        entitlement.process_contract_deltas(orig_access, delta)
        # Cache was not cleaned
        assert expected == entitlement.cfg.read_cache(
            "machine-access-testconcreteentitlement"
        )

    @pytest.mark.parametrize(
        "orig_access,delta",
        (
            (
                {
                    "entitlement": {"entitled": True}
                },  # Full entitlement dropped
                {"entitlement": {"entitled": util.DROPPED_KEY}},
            ),
            (
                {"entitlement": {"entitled": True}},
                {"entitlement": {"entitled": False}},
            ),  # transition to unentitled
        ),
    )
    def test_process_contract_deltas_clean_cache_on_inactive_unentitled(
        self, concrete_entitlement_factory, orig_access, delta, caplog_text
    ):
        """Only clear cache when deltas transition inactive to unentitled."""
        entitlement = concrete_entitlement_factory(
            entitled=True,
            application_status=(status.ApplicationStatus.DISABLED, ""),
        )
        expected = {"entitlement": {"entitled": True}}
        assert expected == entitlement.cfg.read_cache(
            "machine-access-testconcreteentitlement"
        )
        entitlement.process_contract_deltas(orig_access, delta)
        # Cache was cleaned
        assert None is entitlement.cfg.read_cache(
            "machine-access-testconcreteentitlement"
        )
        # If an entitlement is disabled, we don't need to tell the user
        # anything about it becoming unentitled
        # (FIXME: Something on bionic means that DEBUG log lines are being
        # picked up by caplog_text(), so work around that here)
        assert [] == [
            line for line in caplog_text().splitlines() if "DEBUG" not in line
        ]

    @pytest.mark.parametrize(
        "orig_access,delta",
        (
            (
                {
                    "entitlement": {"entitled": True}
                },  # Full entitlement dropped
                {"entitlement": {"entitled": util.DROPPED_KEY}},
            ),
            (
                {"entitlement": {"entitled": True}},
                {"entitlement": {"entitled": False}},
            ),  # transition to unentitled
        ),
    )
    def test_process_contract_deltas_disable_clean_cache_on_active_unentitled(
        self, concrete_entitlement_factory, orig_access, delta
    ):
        """Disable and clear cache when transition active to unentitled."""
        entitlement = concrete_entitlement_factory(
            entitled=True,
            application_status=(status.ApplicationStatus.ENABLED, ""),
        )
        expected = {"entitlement": {"entitled": True}}
        assert expected == entitlement.cfg.read_cache(
            "machine-access-testconcreteentitlement"
        )
        entitlement.process_contract_deltas(orig_access, delta)
        # Cache was cleaned
        assert None is entitlement.cfg.read_cache(
            "machine-access-testconcreteentitlement"
        )
        assert (
            status.ApplicationStatus.DISABLED,
            mock.ANY,
        ) == entitlement.application_status()


class TestUaEntitlementUserFacingStatus:
    def test_inapplicable_when_not_applicable(
        self, concrete_entitlement_factory
    ):
        msg = "inapplicable for very good reasons"
        entitlement = concrete_entitlement_factory(
            entitled=True,
            applicability_status=(
                status.ApplicabilityStatus.INAPPLICABLE,
                msg,
            ),
        )

        user_facing_status, details = entitlement.user_facing_status()
        assert status.UserFacingStatus.INAPPLICABLE == user_facing_status
        assert msg == details

    def test_inapplicable_when_applicable_but_not_entitled(
        self, concrete_entitlement_factory
    ):

        entitlement = concrete_entitlement_factory(
            entitled=False,
            applicability_status=(status.ApplicabilityStatus.APPLICABLE, ""),
        )

        user_facing_status, details = entitlement.user_facing_status()
        assert status.UserFacingStatus.INAPPLICABLE == user_facing_status
        expected_details = "{} is not entitled".format(entitlement.title)
        assert expected_details == details

    def test_inapplicable_when_applicable_but_no_entitlement_cfg(
        self, concrete_entitlement_factory
    ):

        entitlement = concrete_entitlement_factory(
            entitled=False,
            applicability_status=(status.ApplicabilityStatus.APPLICABLE, ""),
        )
        entitlement.cfg._entitlements = {}

        user_facing_status, details = entitlement.user_facing_status()
        assert status.UserFacingStatus.INAPPLICABLE == user_facing_status
        expected_details = "{} is not entitled".format(entitlement.title)
        assert expected_details == details

    @pytest.mark.parametrize(
        "application_status,expected_uf_status",
        (
            (status.ApplicationStatus.ENABLED, status.UserFacingStatus.ACTIVE),
            (
                status.ApplicationStatus.DISABLED,
                status.UserFacingStatus.INACTIVE,
            ),
        ),
    )
    def test_application_status_used_if_not_inapplicable(
        self,
        concrete_entitlement_factory,
        application_status,
        expected_uf_status,
    ):
        msg = "application status details"
        entitlement = concrete_entitlement_factory(
            entitled=True,
            applicability_status=(status.ApplicabilityStatus.APPLICABLE, ""),
            application_status=(application_status, msg),
        )

        user_facing_status, details = entitlement.user_facing_status()
        assert expected_uf_status == user_facing_status
        assert msg == details
