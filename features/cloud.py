import os
import logging
import pycloudlib  # type: ignore
import time
import yaml

from typing import Optional


class Cloud:
    """Base class for cloud providers that should be tested through behave.

    :param tag:
        A tag to be used when creating the resources on the cloud provider
    """

    def __init__(self, tag):
        self.tag = tag
        self._api = None

    def get_instance_id(self, instance):
        """Return the instance identifier.

        :param instance:
            An instance created on the cloud provider
        """
        return instance.id

    @property
    def api(self):
        """Return the api used to interact with the cloud provider."""
        raise NotImplementedError

    def menage_ssh_keys(self, private_key_path=None):
        """Create and manage ssh key pairs to be used in the cloud provider.

        :param private_key_path:
            Location of the private key path to use. If None, the location
            will be a default location.
        """
        raise NotImplementedError

    def _create_instance(
        self,
        series: str,
        image_name: "Optional[str]" = None,
        user_data: "Optional[str]" = None,
    ):
        """Create an instance for on the cloud provider.

        :param series:
            The ubuntu release to be used when creating an instance. We will
            create an image based on this value if the used does not provide
            a image_name value
        :param image_name: 
            The name of the image to be used when creating the instance
        :param user_data:
            The user data to be passed when creating the instance

        :returns:
            An cloud provider instance
        """
        raise NotImplementedError

    def launch(
        self,
        series: str,
        image_name: "Optional[str]" = None,
        user_data: "Optional[str]" = None,
    ):
        """Create and wait for cloud provider instance to be ready.

        :param series:
            The ubuntu release to be used when creating an instance. We will
            create an image based on this value if the used does not provide
            a image_name value
        :param image_name: 
            The name of the image to be used when creating the instance
        :param user_data:
            The user data to be passed when creating the instance

        :returns:
            An cloud provider instance
        """
        inst = self._create_instance(series, image_name, user_data)
        print(
            "--- {} PRO instance launched: {}. Waiting for ssh access".format(
                self.name, inst.id
            )
        )
        time.sleep(15)
        for sleep in (5, 10, 15):
            try:
                inst.wait()
                break
            except Exception as e:
                print("--- Retrying instance.wait on {}".format(str(e)))

        return inst


class EC2(Cloud):
    """Class that represents the EC2 cloud provider.

    :param aws_access_key_id:
        The aws access key id
    :param aws_secret_access_key:
        The aws secret access key
    :region:
        The region to be used to create the aws instances
    :tag:
        A tag to be used when creating the resources on the cloud provider
    """

    EC2_KEY_FILE = "uaclient.pem"
    name = "AWS"

    def __init__(
        self,
        aws_access_key_id,
        aws_secret_access_key,
        region,
        tag="uaclientci",
    ):
        self.aws_access_key_id = None
        self.aws_access_key_id = None
        logging.basicConfig(
            filename="pycloudlib-behave.log", level=logging.DEBUG
        )

        has_aws_keys = bool(aws_access_key_id and aws_secret_access_key)
        if not has_aws_keys:
            logging.warning(
                "UACLIENT_BEHAVE_MACHINE_TYPE=pro.aws requires"
                " the following env vars:\n"
                " - UACLIENT_BEHAVE_AWS_ACCESS_KEY_ID\n"
                " - UACLIENT_BEHAVE_AWS_SECRET_ACCESS_KEY\n"
            )
        else:
            self.aws_access_key_id = aws_access_key_id
            self.aws_secret_access_key = aws_secret_access_key

        self.region = region

        super().__init__(tag)

    @property
    def api(self):
        """Return the api used to interact with the cloud provider."""
        if self._api is None:
            self._api = pycloudlib.EC2(
                tag=self.tag,
                access_key_id=self.aws_access_key_id,
                secret_access_key=self.aws_secret_access_key,
                region=self.region,
            )

        return self._api

    def menage_ssh_keys(self, private_key_path):
        """Create and manage ssh key pairs to be used in the cloud provider.

        :param private_key_path:
            Location of the private key path to use. If None, the location
            will be a default location.
        """
        if not private_key_path:
            private_key_path = self.EC2_KEY_FILE

        if not os.path.exists(private_key_file):
            if "uaclient-integration" in self.api.list_keys():
                self.api.delete_key("uaclient-integration")
            keypair = self.api.client.create_key_pair(
                KeyName="uaclient-integration"
            )

            with open(private_key_file, "w") as stream:
                stream.write(keypair["KeyMaterial"])
            os.chmod(self.EC2_KEY_FILE, 0o600)

        self.api.use_key(
            private_key_file, private_key_file, "uaclient-integration"
        )

    def _create_instance(
        self,
        series: str,
        image_name: "Optional[str]" = None,
        user_data: "Optional[str]" = None,
    ) -> pycloudlib.instance:
        """Launch an instance for on the cloud provider.

        :param series:
            The ubuntu release to be used when creating an instance. We will
            create an image based on this value if the used does not provide
            a image_name value
        :param image_name: 
            The name of the image to be used when creating the instance
        :param user_data:
            The user data to be passed when creating the instance

        :returns:
            An AWS cloud provider instance
        """
        if not image_name:
            if not series:
                raise ValueError(
                    "Must provide either series or image_name to launch_ec2"
                )
            with open("features/aws-ids.yaml", "r") as stream:
                aws_pro_ids = yaml.safe_load(stream.read())
            image_name = aws_pro_ids[series]

        print("--- Launching AWS PRO image {}({})".format(image_name, series))
        vpc = self.api.get_or_create_vpc(name="uaclient-integration")

        try:
            inst = self.api.launch(image_name, user_data=user_data, vpc=vpc)
        except Exception as e:
            print(str(e))
            raise

        return inst


class Azure(Cloud):
    """Class that represents the Azure cloud provider.

    :param az_client_id:
        The Azure client id
    :param az_client_secret
        The Azure client secret
    :param az_tenant_id:
        The Azure tenant id
    :param az_subscription_id:
        The Azure subscription id
    :tag:
        A tag to be used when creating the resources on the cloud provider
    """

    AZURE_PUB_KEY_FILE = "ua_az_pub_key.txt"
    AZURE_PRIV_KEY_FILE = "ua_az_priv_key.txt"
    name = "Azure"

    def __init__(
        self,
        az_client_id,
        az_client_secret,
        az_tenant_id,
        az_subscription_id,
        tag="uaclientci",
    ):
        self.az_client_id = None
        self.az_client_secret = None
        self.az_tenant_id = None
        self.az_subscription_id = None

        has_az_keys = all(
            [az_client_id, az_client_secret, az_tenant_id, az_subscription_id]
        )
        if not has_az_keys:
            logging.warning(
                "UACLIENT_BEHAVE_MACHINE_TYPE=pro.azure requires"
                " the following env vars:\n"
                " - UACLIENT_BEHAVE_AZ_CLIENT_ID\n"
                " - UACLIENT_BEHAVE_AZ_CLIENT_SECRET\n"
                " - UACLIENT_BEHAVE_AZ_TENANT_ID\n"
                " - UACLIENT_BEHAVE_AZ_SUBSCRIPTION_ID\n"
            )
        else:
            self.az_client_id = az_client_id
            self.az_client_secret = az_client_secret
            self.az_tenant_id = az_tenant_id
            self.az_subscription_id = az_subscription_id

        super().__init__(tag)

    @property
    def api(self):
        """Return the api used to interact with the cloud provider."""
        if self._api is None:
            self._api = pycloudlib.Azure(
                tag=self.tag,
                client_id=self.az_client_id,
                client_secret=self.az_client_secret,
                tenant_id=self.az_tenant_id,
                subscription_id=self.az_subscription_id,
            )

        return self._api

    def get_instance_id(self, instance):
        """Return the instance identifier.

        :param instance:
            An instance created on the cloud provider
        """
        # For Azure, the API identifier uses the instance name
        # instead of the instance id
        return instance.name

    def menage_ssh_keys(self, private_key_path=None):
        """Create and manage ssh key pairs to be used in the cloud provider.

        :param private_key_path:
            Location of the private key path to use. If None, the location
            will be a default location.
        """
        if not os.path.exists(self.AZURE_PUB_KEY_FILE):
            if "uaclient-integration" in self.api.list_keys():
                self.api.delete_key("uaclient-integration")
            pub_key, priv_key = self.api.create_key_pair(
                key_name="uaclient-integration"
            )

            with open(self.AZURE_PUB_KEY_FILE, "w") as stream:
                stream.write(pub_key)

            with open(self.AZURE_PRIV_KEY_FILE, "w") as stream:
                stream.write(priv_key)

            os.chmod(self.AZURE_PUB_KEY_FILE, 0o600)
            os.chmod(self.AZURE_PRIV_KEY_FILE, 0o600)

        self.api.use_key(
            self.AZURE_PUB_KEY_FILE,
            self.AZURE_PRIV_KEY_FILE,
            "uaclient-integration",
        )

    def _create_instance(
        self,
        series: str,
        image_name: "Optional[str]" = None,
        user_data: "Optional[str]" = None,
    ) -> pycloudlib.instance:
        """Launch an instance for on the cloud provider.

        :param series:
            The ubuntu release to be used when creating an instance. We will
            create an image based on this value if the used does not provide
            a image_name value
        :param image_name: 
            The name of the image to be used when creating the instance
        :param user_data:
            The user data to be passed when creating the instance

        :returns:
            An AWS cloud provider instance
        """
        if not image_name:
            if not series:
                raise ValueError(
                    "Must provide either series or image_name to launch azure"
                )
            with open("features/azure-ids.yaml", "r") as stream:
                aws_pro_ids = yaml.safe_load(stream.read())
            image_name = aws_pro_ids[series]

        print(
            "--- Launching Azure PRO image {}({})".format(image_name, series)
        )
        inst = self.api.launch(image_id=image_name, user_data=user_data)
        return inst
