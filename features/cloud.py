import json
import logging
import os
import time
from typing import List, Optional

import pycloudlib  # type: ignore
import toml
from pycloudlib.cloud import ImageType  # type: ignore

DEFAULT_CONFIG_PATH = "~/.config/pycloudlib.toml"


class Cloud:
    """Base class for cloud providers that should be tested through behave.

    :cloud_credentials_path:
        A string containing the path for the pycloudlib cloud credentials file
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

    def __init__(
        self,
        machine_type: str,
        cloud_credentials_path: Optional[str],
        tag: Optional[str] = None,
        timestamp_suffix: bool = True,
    ) -> None:
        if tag:
            self.tag = tag
        else:
            self.tag = "uaclient-ci"
        self.machine_type = machine_type
        self._api = None
        self.key_name = pycloudlib.util.get_timestamped_tag(self.tag)
        self.timestamp_suffix = timestamp_suffix
        self.cloud_credentials_path = cloud_credentials_path

    @property
    def pycloudlib_cls(self):
        """Return the pycloudlib cls to be used as an api."""
        raise NotImplementedError

    @property
    def api(self) -> pycloudlib.cloud.BaseCloud:
        """Return the api used to interact with the cloud provider."""
        if self._api is None:
            self._api = self.pycloudlib_cls(
                config_file=self.cloud_credentials_path,
                tag=self.tag,
                timestamp_suffix=self.timestamp_suffix,
            )

        return self._api

    def _create_instance(
        self,
        series: str,
        instance_name: Optional[str] = None,
        image_name: Optional[str] = None,
        user_data: Optional[str] = None,
        ephemeral: bool = False,
        inbound_ports: Optional[List[str]] = None,
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
        :param ephemeral:
            If instance should be ephemeral
        :param inbound_ports:
            List of ports to open for network ingress to the instance

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

        logging.info("--- cloud-init succeeded")

    def launch(
        self,
        series: str,
        instance_name: Optional[str] = None,
        image_name: Optional[str] = None,
        user_data: Optional[str] = None,
        ephemeral: bool = False,
        inbound_ports: Optional[List[str]] = None,
        cloud_init_ppa: Optional[str] = None,
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
        :param ephemeral:
            If instance should be ephemeral
        :param inbound_ports:
            List of ports to open for network ingress to the instance
        :param cloud_init_ppa:
            Cloud-init's ppa to upgrade with

        :returns:
            An cloud provider instance
        """
        inst = self._create_instance(
            series=series,
            instance_name=instance_name,
            image_name=image_name,
            user_data=user_data,
            ephemeral=ephemeral,
            inbound_ports=inbound_ports,
        )
        logging.info(
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
                logging.info("--- Retrying instance.wait on {}".format(str(e)))

        if cloud_init_ppa:
            logging.info("--- Installing cloud-init PPA: %s", cloud_init_ppa)
            assert inst.execute(
                "sudo add-apt-repository {} -y".format(cloud_init_ppa)
            ).ok
            assert inst.execute("sudo apt-get update -q").ok
            assert inst.execute("sudo apt-get install -qy cloud-init").ok
            assert inst.execute("sudo cloud-init clean --logs").ok
        else:
            # Check only if cloud-init wasn't upgraded as given user-data could
            # be only compatible with the newer version.
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

        image_type = ImageType.GENERIC
        if "pro.fips" in self.machine_type:
            image_type = ImageType.PRO_FIPS
        elif "pro" in self.machine_type:
            image_type = ImageType.PRO

        return self.api.daily_image(release=series, image_type=image_type)

    def manage_ssh_key(
        self,
        private_key_path: Optional[str] = None,
        key_name: Optional[str] = None,
    ) -> None:
        """Create and manage ssh key pairs to be used in the cloud provider.

        :param private_key_path:
            Location of the private key path to use. If None, the location
            will be a default location.
        """
        if key_name:
            self.key_name = key_name
        cloud_name = self.name.lower().replace("_", "-")
        pub_key_path = "{}-pub-{}".format(cloud_name, self.key_name)
        priv_key_path = "{}-priv-{}".format(cloud_name, self.key_name)
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
    """Class that represents the EC2 cloud provider."""

    name = "aws"

    @property
    def pycloudlib_cls(self):
        """Return the pycloudlib cls to be used as an api."""
        return pycloudlib.EC2

    def manage_ssh_key(
        self,
        private_key_path: Optional[str] = None,
        key_name: Optional[str] = None,
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
            logging.info(
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
        instance_name: Optional[str] = None,
        image_name: Optional[str] = None,
        user_data: Optional[str] = None,
        ephemeral: bool = False,
        inbound_ports: Optional[List[str]] = None,
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
        :param ephemeral:
            If instance should be ephemeral
        :param inbound_ports:
            List of ports to open for network ingress to the instance

        :returns:
            An AWS cloud provider instance
        """
        if not image_name:
            image_name = self.locate_image_name(series)

        logging.info(
            "--- Launching AWS image {}({})".format(image_name, series)
        )
        vpc = self.api.get_or_create_vpc(name="uaclient-integration")

        try:
            inst = self.api.launch(image_name, user_data=user_data, vpc=vpc)
        except Exception as e:
            logging.error(str(e))
            raise

        return inst


class Azure(Cloud):
    """Class that represents the Azure cloud provider."""

    name = "Azure"

    @property
    def pycloudlib_cls(self):
        """Return the pycloudlib cls to be used as an api."""
        return pycloudlib.Azure

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

    def manage_ssh_key(
        self,
        private_key_path: Optional[str] = None,
        key_name: Optional[str] = None,
    ) -> None:
        """Create and manage ssh key pairs to be used in the cloud provider.

        :param private_key_path:
            Location of the private key path to use. If None, the location
            will be a default location.
        """
        if not private_key_path:
            private_key_path = "azure-priv-{}.pem".format(self.key_name)
            pub_key_path = "azure-pub-{}.txt".format(self.key_name)
            logging.info(
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
        instance_name: Optional[str] = None,
        image_name: Optional[str] = None,
        user_data: Optional[str] = None,
        ephemeral: bool = False,
        inbound_ports: Optional[List[str]] = None,
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
        :param ephemeral:
            If instance should be ephemeral
        :param inbound_ports:
            List of ports to open for network ingress to the instance

        :returns:
            An Azure cloud provider instance
        """
        if not image_name:
            image_name = self.locate_image_name(series)

        logging.info(
            "--- Launching Azure image {}({})".format(image_name, series)
        )
        inst = self.api.launch(
            image_id=image_name,
            instance_type="Standard_A2_v2",
            user_data=user_data,
            inbound_ports=inbound_ports,
        )
        return inst


class GCP(Cloud):
    """Class that represents the Google Cloud Platform cloud provider."""

    name = "gcp"
    cls_type = pycloudlib.GCE

    @property
    def pycloudlib_cls(self):
        """Return the pycloudlib cls to be used as an api."""
        return pycloudlib.GCE

    def __init__(
        self,
        machine_type: str,
        cloud_credentials_path: Optional[str],
        tag: Optional[str] = None,
        timestamp_suffix: bool = True,
    ) -> None:
        super().__init__(
            machine_type=machine_type,
            cloud_credentials_path=cloud_credentials_path,
            tag=tag,
            timestamp_suffix=timestamp_suffix,
        )
        self._set_service_account_email()

    def _set_service_account_email(self):
        """Set service account email if credentials provided."""
        credentials_path = (
            self.cloud_credentials_path
            or os.getenv("PYCLOUDLIB_CONFIG")
            or DEFAULT_CONFIG_PATH
        )
        json_credentials = {}

        try:
            credentials = toml.load(os.path.expanduser(credentials_path))
        except toml.TomlDecodeError:
            raise ValueError(
                "Could not parse configuration file pointed to by "
                "{}".format(credentials_path)
            )

        # Use service_account_email from pycloudlib.toml if defined
        self.service_account_email = credentials.get("gce", {}).get(
            "service_account_email"
        )
        if self.service_account_email:
            return

        gcp_credentials_path = os.path.expandvars(
            os.path.expanduser(
                credentials.get("gce", {}).get("credentials_path")
            )
        )
        if gcp_credentials_path:
            with open(gcp_credentials_path, "r") as f:
                json_credentials = json.load(f)

        self.service_account_email = json_credentials.get("client_email")

    @property
    def api(self) -> pycloudlib.cloud.BaseCloud:
        """Return the api used to interact with the cloud provider."""
        if self._api is None:
            self._api = self.pycloudlib_cls(
                config_file=self.cloud_credentials_path,
                tag=self.tag,
                timestamp_suffix=self.timestamp_suffix,
                service_account_email=self.service_account_email,
            )

        return self._api

    def _create_instance(
        self,
        series: str,
        instance_name: Optional[str] = None,
        image_name: Optional[str] = None,
        user_data: Optional[str] = None,
        ephemeral: bool = False,
        inbound_ports: Optional[List[str]] = None,
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
        :param ephemeral:
            If instance should be ephemeral
        :param inbound_ports:
            List of ports to open for network ingress to the instance

        :returns:
            An GCP cloud provider instance
        """
        if not image_name:
            image_name = self.locate_image_name(series)

        logging.info(
            "--- Launching GCP image {}({})".format(image_name, series)
        )
        inst = self.api.launch(image_id=image_name, user_data=user_data)
        return inst


class _LXD(Cloud):
    name = "_lxd"

    def _create_instance(
        self,
        series: str,
        instance_name: Optional[str] = None,
        image_name: Optional[str] = None,
        user_data: Optional[str] = None,
        ephemeral: bool = False,
        inbound_ports: Optional[List[str]] = None,
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
        :param ephemeral:
            If instance should be ephemeral
        :param inbound_ports:
            List of ports to open for network ingress to the instance

        :returns:
            An AWS cloud provider instance
        """
        if not image_name:
            image_name = self.locate_image_name(series)

        image_type = self.name.title().replace("-", " ")

        logging.info(
            "--- Launching {} image {}({})".format(
                image_type, image_name, series
            )
        )

        if self.name == "lxd-virtual-machine" and series == "xenial":
            # Livepatch won't apply patches on Xenial with secure boot enabled
            config_dict = {"security.secureboot": False}
        else:
            config_dict = {}

        inst = self.api.launch(
            name=instance_name,
            image_id=image_name,
            user_data=user_data,
            ephemeral=ephemeral,
            config_dict=config_dict,
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
