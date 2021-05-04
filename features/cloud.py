import json
import os
import logging
import pycloudlib  # type: ignore
import time
import yaml

try:
    from typing import Tuple, List, Optional  # noqa
except ImportError:
    # typing isn't available on trusty, so ignore its absence
    pass


class Cloud:
    """Base class for cloud providers that should be tested through behave.

    :machine_type:
        A string representing the type of machine to launch (pro or generic)
    :region:
        The region to create the cloud resources on
    :param tag:
        A tag to be used when creating the resources on the cloud provider
    :timestamp_suffix:
        Boolean set true to direct pycloudlib to append a timestamp to the end
        of the provided tag.
    """

    name = ""
    pro_ids_path = ""
    env_vars: "Tuple[str, ...]" = ()

    def __init__(
        self,
        machine_type: str,
        region: "Optional[str]" = None,
        tag: "Optional[str]" = None,
        timestamp_suffix: bool = True,
    ) -> None:
        if tag:
            self.tag = tag
        else:
            self.tag = "uaclient-ci"
        self.machine_type = machine_type
        self.region = region
        self._api = None
        self.key_name = pycloudlib.util.get_timestamped_tag(self.tag)
        self.timestamp_suffix = timestamp_suffix

        missing_env_vars = self.missing_env_vars()
        if missing_env_vars:
            logging.warning(
                "".join(
                    [
                        "UACLIENT_BEHAVE_MACHINE_TYPE={} requires".format(
                            self.machine_type
                        ),
                        " the following env vars:\n",
                        *self.format_missing_env_vars(missing_env_vars),
                    ]
                )
            )

    @property
    def api(self) -> pycloudlib.cloud.BaseCloud:
        """Return the api used to interact with the cloud provider."""
        raise NotImplementedError

    def _create_instance(
        self,
        series: str,
        instance_name: "Optional[str]" = None,
        image_name: "Optional[str]" = None,
        user_data: "Optional[str]" = None,
    ) -> pycloudlib.instance:
        """Create an instance for on the cloud provider.

        :param series:
            The ubuntu release to be used when creating an instance. We will
            create an image based on this value if the used does not provide
            a image_name value
        :param instance_name:
            The name of the instance to be created
        :param image_name:
            The name of the image to be used when creating the instance
        :param user_data:
            The user data to be passed when creating the instance

        :returns:
            A cloud provider instance
        """
        raise NotImplementedError

    def _check_cloudinit_status(
        self, instance: pycloudlib.instance.BaseInstance
    ) -> None:
        """
        Check if cloudinit was able to finish without errors.

        :param instance:
            An instance created on the cloud provider
        """
        result = instance.execute(["cloud-init", "status", "--wait", "--long"])

        if result.failed:
            raise OSError(
                "cloud-init failed to start\n: out: %s\n error: %s"
                % (result.stdout, result.stderr)
            )

        print("--- cloud-init succeeded")

    def launch(
        self,
        series: str,
        instance_name: "Optional[str]" = None,
        image_name: "Optional[str]" = None,
        user_data: "Optional[str]" = None,
    ) -> pycloudlib.instance.BaseInstance:
        """Create and wait for cloud provider instance to be ready.

        :param series:
            The ubuntu release to be used when creating an instance. We will
            create an image based on this value if the used does not provide
            a image_name value
        :param instance_name:
            The name of the instance to be created
        :param image_name:
            The name of the image to be used when creating the instance
        :param user_data:
            The user data to be passed when creating the instance

        :returns:
            An cloud provider instance
        """
        inst = self._create_instance(
            series=series,
            instance_name=instance_name,
            image_name=image_name,
            user_data=user_data,
        )
        print(
            "--- {} instance launched: {}. Waiting for ssh access".format(
                self.name, inst.name
            )
        )
        time.sleep(15)
        for sleep in (5, 10, 15):
            try:
                inst.wait()
                break
            except Exception as e:
                print("--- Retrying instance.wait on {}".format(str(e)))

        self._check_cloudinit_status(inst)
        return inst

    def get_instance_id(
        self, instance: pycloudlib.instance.BaseInstance
    ) -> str:
        """Return the instance identifier.

        :param instance:
            An instance created on the cloud provider

        :returns:
            The string of the unique instance id
        """
        return instance.id

    def format_missing_env_vars(self, missing_env_vars: "List") -> "List[str]":
        """Format missing env vars to be displayed in log.

        :returns:
            A list of env string formatted to be used when logging
        """
        return [" - {}\n".format(env_var) for env_var in missing_env_vars]

    def missing_env_vars(self) -> "List[str]":
        """Return a list of env variables necessary for this cloud provider.

        :returns:
            A list of string representing the missing variables
        """
        return [
            env_name
            for env_name in self.env_vars
            if not getattr(
                self, env_name.lower().replace("uaclient_behave_", "")
            )
        ]

    def locate_image_name(self, series: str) -> str:
        """Locate and return the image name to use for vm provision.

        :param series:
            The ubuntu release to be used when locating the image name

        :returns:
            A image name to use when provisioning a virtual machine
            based on the series value
        """
        if not series:
            raise ValueError(
                "Must provide either series or image_name to launch azure"
            )

        if "pro" in self.machine_type:
            with open(self.pro_ids_path, "r") as stream:
                pro_ids = yaml.safe_load(stream.read())
            image_name = pro_ids[series]
        else:
            image_name = self.api.daily_image(release=series)

        return image_name

    def manage_ssh_key(self, private_key_path: "Optional[str]" = None) -> None:
        """Create and manage ssh key pairs to be used in the cloud provider.

        :param private_key_path:
            Location of the private key path to use. If None, the location
            will be a default location.
        """
        cloud_name = self.name.lower().replace("_", "-")
        pub_key_path = "{}-pubkey".format(cloud_name)
        priv_key_path = "{}-privkey".format(cloud_name)
        pub_key, priv_key = self.api.create_key_pair()

        with open(pub_key_path, "w") as f:
            f.write(pub_key)

        with open(priv_key_path, "w") as f:
            f.write(priv_key)

        os.chmod(pub_key_path, 0o600)
        os.chmod(priv_key_path, 0o600)

        self.api.use_key(
            public_key_path=pub_key_path, private_key_path=priv_key_path
        )


class EC2(Cloud):
    """Class that represents the EC2 cloud provider.

    :param aws_access_key_id:
        The aws access key id
    :param aws_secret_access_key:
        The aws secret access key
    :region:
        The region to be used to create the aws instances
    :machine_type:
        A string representing the type of machine to launch (pro or generic)
    :tag:
        A tag to be used when creating the resources on the cloud provider
    :timestamp_suffix:
        Boolean set true to direct pycloudlib to append a timestamp to the end
        of the provided tag.
    """

    name = "aws"
    env_vars: "Tuple[str, ...]" = (
        "aws_access_key_id",
        "aws_secret_access_key",
    )
    pro_ids_path = "features/aws-ids.yaml"

    def __init__(
        self,
        aws_access_key_id: "Optional[str]",
        aws_secret_access_key: "Optional[str]",
        machine_type: str,
        region: "Optional[str]" = "us-east-2",
        tag: "Optional[str]" = None,
        timestamp_suffix: bool = True,
    ) -> None:
        self.aws_access_key_id = aws_access_key_id
        self.aws_secret_access_key = aws_secret_access_key
        logging.basicConfig(
            filename="pycloudlib-behave.log", level=logging.DEBUG
        )
        super().__init__(
            region=region,
            machine_type=machine_type,
            tag=tag,
            timestamp_suffix=timestamp_suffix,
        )

    @property
    def api(self) -> pycloudlib.cloud.BaseCloud:
        """Return the api used to interact with the cloud provider."""
        if self._api is None:
            self._api = pycloudlib.EC2(
                tag=self.tag,
                access_key_id=self.aws_access_key_id,
                secret_access_key=self.aws_secret_access_key,
                region=self.region,
                timestamp_suffix=self.timestamp_suffix,
            )

        return self._api

    def manage_ssh_key(
        self,
        private_key_path: "Optional[str]" = None,
        key_name: "Optional[str]" = None,
    ) -> None:
        """Create and manage ssh key pairs to be used in the cloud provider.

        :param private_key_path:
            Location of the private key path to use. If None, the location
            will be a default location.
        :param key_name:
            Optional key_name to use when uploading to the cloud. Default is
            uaclient-ci-<timestamp>
        """
        if key_name:
            self.key_name = key_name
        if not private_key_path:
            if self.key_name in self.api.list_keys():
                self.api.delete_key(self.key_name)

            private_key_path = "ec2-{}.pem".format(self.key_name)
            print(
                "--- Creating local keyfile {} for EC2".format(
                    private_key_path
                )
            )
            keypair = self.api.client.create_key_pair(KeyName=self.key_name)

            with open(private_key_path, "w") as stream:
                stream.write(keypair["KeyMaterial"])
            os.chmod(private_key_path, 0o600)

        self.api.use_key(private_key_path, private_key_path, self.key_name)

    def _create_instance(
        self,
        series: str,
        instance_name: "Optional[str]" = None,
        image_name: "Optional[str]" = None,
        user_data: "Optional[str]" = None,
    ) -> pycloudlib.instance:
        """Launch an instance on the cloud provider.

        :param series:
            The ubuntu release to be used when creating an instance. We will
            create an image based on this value if the used does not provide
            a image_name value
        :param instance_name:
            The name of the instance to be created
        :param image_name:
            The name of the image to be used when creating the instance
        :param user_data:
            The user data to be passed when creating the instance

        :returns:
            An AWS cloud provider instance
        """
        if not image_name:
            image_name = self.locate_image_name(series)

        print("--- Launching AWS image {}({})".format(image_name, series))
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
    :machine_type:
        A string representing the type of machine to launch (pro or generic)
    :region:
        The region to create the resources on
    :tag:
        A tag to be used when creating the resources on the cloud provider
    :timestamp_suffix:
        Boolean set true to direct pycloudlib to append a timestamp to the end
        of the provided tag.
    """

    name = "Azure"
    env_vars: "Tuple[str, ...]" = (
        "az_client_id",
        "az_client_secret",
        "az_tenant_id",
        "az_subscription_id",
    )
    pro_ids_path = "features/azure-ids.yaml"

    def __init__(
        self,
        machine_type: str,
        region: "Optional[str]" = "centralus",
        tag: "Optional[str]" = None,
        timestamp_suffix: bool = True,
        az_client_id: "Optional[str]" = None,
        az_client_secret: "Optional[str]" = None,
        az_tenant_id: "Optional[str]" = None,
        az_subscription_id: "Optional[str]" = None,
    ) -> None:
        self.az_client_id = az_client_id
        self.az_client_secret = az_client_secret
        self.az_tenant_id = az_tenant_id
        self.az_subscription_id = az_subscription_id

        super().__init__(
            machine_type=machine_type,
            region=region,
            tag=tag,
            timestamp_suffix=timestamp_suffix,
        )

    @property
    def api(self) -> pycloudlib.cloud.BaseCloud:
        """Return the api used to interact with the cloud provider."""
        if self._api is None:
            self._api = pycloudlib.Azure(
                tag=self.tag,
                client_id=self.az_client_id,
                client_secret=self.az_client_secret,
                tenant_id=self.az_tenant_id,
                subscription_id=self.az_subscription_id,
                timestamp_suffix=self.timestamp_suffix,
            )

        return self._api

    def get_instance_id(
        self, instance: pycloudlib.instance.BaseInstance
    ) -> str:
        """Return the instance identifier.

        :param instance:
            An instance created on the cloud provider

        :returns:
            The string of the unique instance id
        """
        # For Azure, the API identifier uses the instance name
        # instead of the instance id
        return instance.name

    def manage_ssh_key(self, private_key_path: "Optional[str]" = None) -> None:
        """Create and manage ssh key pairs to be used in the cloud provider.

        :param private_key_path:
            Location of the private key path to use. If None, the location
            will be a default location.
        """
        if not private_key_path:
            private_key_path = "azure-priv-{}.pem".format(self.key_name)
            pub_key_path = "azure-pub-{}.txt".format(self.key_name)
            print(
                "--- Creating local keyfile {} for Azure".format(
                    private_key_path
                )
            )
        if not os.path.exists(private_key_path):
            pub_key, priv_key = self.api.create_key_pair(
                key_name=self.key_name
            )

            with open(pub_key_path, "w") as stream:
                stream.write(pub_key)

            with open(private_key_path, "w") as stream:
                stream.write(priv_key)

            os.chmod(pub_key_path, 0o600)
            os.chmod(private_key_path, 0o600)

        self.api.use_key(pub_key_path, private_key_path, self.key_name)

    def _create_instance(
        self,
        series: str,
        instance_name: "Optional[str]" = None,
        image_name: "Optional[str]" = None,
        user_data: "Optional[str]" = None,
    ) -> pycloudlib.instance:
        """Launch an instance on the cloud provider.

        :param series:
            The ubuntu release to be used when creating an instance. We will
            create an image based on this value if the used does not provide
            a image_name value
        :param instance_name:
            The name of the instance to be created
        :param image_name:
            The name of the image to be used when creating the instance
        :param user_data:
            The user data to be passed when creating the instance

        :returns:
            An AWS cloud provider instance
        """
        if not image_name:
            image_name = self.locate_image_name(series)

        print("--- Launching Azure image {}({})".format(image_name, series))
        inst = self.api.launch(image_id=image_name, user_data=user_data)
        return inst


class GCP(Cloud):
    name = "gcp"
    pro_ids_path = "features/gcp-ids.yaml"

    """Class that represents the Google Cloud Platform cloud provider.

    :param gcp_credentials_path
        The GCP credentials path to use when authentiacting to GCP
    :param gcp_project
        The name of the GCP project to be used
    :machine_type:
        A string representing the type of machine to launch (pro or generic)
    :region:
        The region to create the resources on
    :tag:
        A tag to be used when creating the resources on the cloud provider
    :timestamp_suffix:
        Boolean set true to direct pycloudlib to append a timestamp to the end
        of the provided tag.
    """

    env_vars: "Tuple[str, ...]" = ("gcp_credentials_path", "gcp_project")

    def __init__(
        self,
        machine_type: str,
        region: "Optional[str]" = "us-west2",
        tag: "Optional[str]" = None,
        timestamp_suffix: bool = True,
        zone: "Optional[str]" = "a",
        gcp_credentials_path: "Optional[str]" = None,
        gcp_project: "Optional[str]" = None,
    ) -> None:
        self.gcp_credentials_path = gcp_credentials_path
        self.gcp_project = gcp_project
        self.zone = zone

        super().__init__(
            machine_type=machine_type,
            region=region,
            tag=tag,
            timestamp_suffix=timestamp_suffix,
        )

        self._set_service_account_email()

    def _set_service_account_email(self):
        """Set service account email if credentials provided."""
        json_credentials = {}

        if self.gcp_credentials_path:
            with open(self.gcp_credentials_path, "r") as f:
                json_credentials = json.load(f)

        self.service_account_email = json_credentials.get("client_email")

    @property
    def api(self) -> pycloudlib.cloud.BaseCloud:
        """Return the api used to interact with the cloud provider."""
        if self._api is None:
            self._api = pycloudlib.GCE(
                tag=self.tag,
                timestamp_suffix=self.timestamp_suffix,
                credentials_path=self.gcp_credentials_path,
                project=self.gcp_project,
                zone=self.zone,
                region=self.region,
                service_account_email=self.service_account_email,
            )

        return self._api

    def _create_instance(
        self,
        series: str,
        instance_name: "Optional[str]" = None,
        image_name: "Optional[str]" = None,
        user_data: "Optional[str]" = None,
    ) -> pycloudlib.instance:
        """Launch an instance on the cloud provider.

        :param series:
            The ubuntu release to be used when creating an instance. We will
            create an image based on this value if the used does not provide
            a image_name value
        :param instance_name:
            The name of the instance to be created
        :param image_name:
            The name of the image to be used when creating the instance
        :param user_data:
            The user data to be passed when creating the instance

        :returns:
            An AWS cloud provider instance
        """
        if not image_name:
            image_name = self.locate_image_name(series)

        print("--- Launching GCP image {}({})".format(image_name, series))
        inst = self.api.launch(image_id=image_name, user_data=user_data)
        return inst


class _LXD(Cloud):
    name = "_lxd"

    @property
    def pycloudlib_cls(self):
        """Return the pycloudlib cls to be used as an api."""
        raise NotImplementedError

    def _create_instance(
        self,
        series: str,
        instance_name: "Optional[str]" = None,
        image_name: "Optional[str]" = None,
        user_data: "Optional[str]" = None,
    ) -> pycloudlib.instance:
        """Launch an instance on the cloud provider.

        :param series:
            The ubuntu release to be used when creating an instance. We will
            create an image based on this value if the used does not provide
            a image_name value
        :param instance_name:
            The name of the instance to be created
        :param image_name:
            The name of the image to be used when creating the instance
        :param user_data:
            The user data to be passed when creating the instance

        :returns:
            An AWS cloud provider instance
        """
        if not image_name:
            image_name = self.locate_image_name(series)

        image_type = self.name.title().replace("-", " ")

        print(
            "--- Launching {} image {}({})".format(
                image_type, image_name, series
            )
        )

        inst = self.api.launch(
            name=instance_name, image_id=image_name, user_data=user_data
        )
        return inst

    def get_instance_id(
        self, instance: pycloudlib.instance.BaseInstance
    ) -> str:
        """Return the instance identifier.

        :param instance:
            An instance created on the cloud provider

        :returns:
            The string of the unique instance id
        """
        # For LXD, the API identifier uses the instance name
        # instead of the instance id
        return instance.name

    def locate_image_name(self, series: str) -> str:
        """Locate and return the image name to use for vm provision.

        :param series:
            The ubuntu release to be used when locating the image name

        :returns:
            A image name to use when provisioning a virtual machine
            based on the series value
        """
        if not series:
            raise ValueError(
                "Must provide either series or image_name to launch azure"
            )

        image_name = self.api.daily_image(release=series)
        return image_name

    @property
    def api(self) -> pycloudlib.cloud.BaseCloud:
        """Return the api used to interact with the cloud provider."""
        if self._api is None:
            self._api = self.pycloudlib_cls(
                tag=self.tag, timestamp_suffix=self.timestamp_suffix
            )

        return self._api


class LXDVirtualMachine(_LXD):
    name = "lxd-virtual-machine"

    @property
    def pycloudlib_cls(self):
        """Return the pycloudlib cls to be used as an api."""
        return pycloudlib.LXDVirtualMachine


class LXDContainer(_LXD):
    name = "lxd-container"

    @property
    def pycloudlib_cls(self):
        """Return the pycloudlib cls to be used as an api."""
        return pycloudlib.LXDContainer
