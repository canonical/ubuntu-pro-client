import mock
import pytest

from uaclient import exceptions
from uaclient.api.u.pro.attach.auto.should_auto_attach.v1 import (
    _should_auto_attach,
)

M_PATH = "uaclient.api.u.pro.attach.auto.should_auto_attach.v1"


class TestShouldAutoAttachV1:
    @pytest.mark.parametrize(
        "expected,installed_pkgs",
        (
            (True, ("foo", "ubuntu-advantage-pro", "bar")),
            (False, ("foo", "bar")),
        ),
    )
    @mock.patch(M_PATH + ".cloud_instance_factory")
    @mock.patch("uaclient.apt.get_installed_packages_names")
    def test_detect_is_pro(
        self,
        m_get_installed_pkgs,
        _m_cloud_factory,
        expected,
        installed_pkgs,
        FakeConfig,
    ):
        m_get_installed_pkgs.return_value = installed_pkgs
        assert expected == _should_auto_attach(FakeConfig()).should_auto_attach

    @pytest.mark.parametrize(
        "cloud_exception",
        (
            (exceptions.CloudFactoryNoCloudError),
            (exceptions.CloudFactoryUnsupportedCloudError),
            (exceptions.CloudFactoryNonViableCloudError),
        ),
    )
    @mock.patch(M_PATH + ".cloud_instance_factory")
    def test_detect_is_pro_when_cloud_factory_fails(
        self,
        m_cloud_factory,
        cloud_exception,
        FakeConfig,
    ):
        m_cloud_factory.side_effect = cloud_exception(cloud_type="test")
        assert False is _should_auto_attach(FakeConfig()).should_auto_attach
