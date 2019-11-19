import mock

import pytest

from uaclient.clouds.aws import UAPremiumAWSInstance

M_PATH = "uaclient.clouds.aws."


class TestUAPremiumAWSInstance:
    @mock.patch(M_PATH + "util.readurl")
    def test_identity_doc_from_aws_url_pkcs7(self, readurl):
        """Return pkcs7 content from IMDS as AWS' identity doc"""
        readurl.return_value = "pkcs7WOOT!==", {"header": "stuff"}
        instance = UAPremiumAWSInstance()
        assert "pkcs7WOOT!==" == instance.identity_doc
        url = "http://169.254.169.254/latest/dynamic/instance-identity/pkcs7"
        assert [mock.call(url)] == readurl.call_args_list

    @pytest.mark.parametrize("uuid", ("ec2", "ec2yep"))
    @mock.patch(M_PATH + "util.load_file")
    def test_is_viable_based_on_sys_hypervisor_uuid(self, load_file, uuid):
        """Viable ec2 platform is determined by /sys/hypervisor/uuid prefix"""
        load_file.return_value = uuid
        instance = UAPremiumAWSInstance()
        assert True is instance.is_viable

    @pytest.mark.parametrize(
        "hypervisor_uuid,prod_uuid,prod_serial,viable",
        (
            ("notec2", "ec2UUID", "ec2Serial", True),
            ("notec2", "EC2UUID", "Ec2Serial", True),
            ("notec2", "!EC2UUID", "Ec2Serial", False),
            ("notec2", "EC2UUID", "1Ec2Serial", False),
            ("notec2", "ec2UUID", "ec3Serial", False),
            ("notec2", "ec3UUID", "ec2Serial", False),
        ),
    )
    @mock.patch(M_PATH + "util.load_file")
    def test_is_viable_based_on_sys_product_serial_and_uuid(
        self, load_file, hypervisor_uuid, prod_uuid, prod_serial, viable
    ):
        """Platform is viable when product serial and uuid start with ec2"""

        def fake_load_file(f_name):
            if f_name == "/sys/hypervisor/uuid":
                return hypervisor_uuid
            if f_name == "/sys/class/dmi/id/product_uuid":
                return prod_uuid
            if f_name == "/sys/class/dmi/id/product_serial":
                return prod_serial
            raise AssertionError("Invalid load_file of {}".format(f_name))

        load_file.side_effect = fake_load_file
        instance = UAPremiumAWSInstance()
        assert viable is instance.is_viable
