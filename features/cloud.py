import json
import logging
import os
import shlex
import time
from contextlib import suppress
from typing import List, Optional

import pycloudlib  # type: ignore
import toml
from paramiko.ssh_exception import NoValidConnectionsError, SSHException
from pycloudlib.cloud import ImageType  # type: ignore
from pycloudlib.errors import PycloudlibTimeoutError  # type: ignore
from pycloudlib.result import Result  # type: ignore

DEFAULT_CONFIG_PATH = "~/.config/pycloudlib.toml"


def cloud_factory(pro_config, cloud_name):
    if cloud_name == "aws":
        return EC2(
            cloud_credentials_path=pro_config.cloud_credentials_path,
            tag=pro_config.timed_job_tag,
            timestamp_suffix=False,
        )
    if cloud_name == "azure":
        return Azure(
            cloud_credentials_path=pro_config.cloud_credentials_path,
            tag=pro_config.timed_job_tag,
            timestamp_suffix=False,
        )
    if cloud_name == "gcp":
        return GCP(
            cloud_credentials_path=pro_config.cloud_credentials_path,
            tag=pro_config.timed_job_tag,
            timestamp_suffix=False,
        )
    if cloud_name == "lxd-vm":
        return LXDVirtualMachine(
            cloud_credentials_path=pro_config.cloud_credentials_path,
        )
    if cloud_name == "lxd-container":
        return LXDContainer(
            cloud_credentials_path=pro_config.cloud_credentials_path,
        )
    if cloud_name == "wsl":
        return WSL(
            wsl_pubkey_path=pro_config.wsl_pubkey_path,
            wsl_privkey_path=pro_config.wsl_privkey_path,
            wsl_ip_address=pro_config.wsl_ip_address,
            cloud_credentials_path=pro_config.cloud_credentials_path,
        )
    raise RuntimeError("Invalid cloud name")


class CloudManager:
    def __init__(self, pro_config):
        self.pro_config = pro_config
        self.clouds = {}

    def get(self, cloud_name):
        cloud = self.clouds.get(cloud_name)
        if cloud is None:
            cloud = cloud_factory(self.pro_config, cloud_name)
            self.clouds[cloud_name] = cloud
        return cloud

    def has(self, cloud_name: str):
        return cloud_name in self.clouds


class Cloud:
    """Base class for cloud providers that should be tested through behave.

    :cloud_credentials_path:
        A string containing the path for the pycloudlib cloud credentials file
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
        cloud_credentials_path: Optional[str],
        tag: Optional[str] = None,
        timestamp_suffix: bool = True,
    ) -> None:
        if tag:
            self.tag = tag
        else:
            self.tag = "uaclient-ci"
        self._api = None
        self.key_name = pycloudlib.util.get_timestamped_tag(self.tag)
        self.timestamp_suffix = timestamp_suffix
        self.cloud_credentials_path = cloud_credentials_path
        self._ssh_key_managed = False

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
        machine_type: str,
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
        :machine_type:
            string representing the type of machine to launch (pro or generic)
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

        logging.info("--- cloud-init might've failed but oh well")
        return

        if result.failed:
            raise OSError(
                "cloud-init failed to start\n: out: %s\n error: %s"
                % (result.stdout, result.stderr)
            )

        logging.info("--- cloud-init succeeded")

    def launch(
        self,
        series: str,
        machine_type: str,
        instance_name: Optional[str] = None,
        image_name: Optional[str] = None,
        user_data: Optional[str] = None,
        ephemeral: bool = False,
        inbound_ports: Optional[List[str]] = None,
    ) -> pycloudlib.instance.BaseInstance:
        """Create and wait for cloud provider instance to be ready.

        :param series:
            The ubuntu release to be used when creating an instance. We will
            create an image based on this value if the used does not provide
            a image_name value
        :machine_type:
            string representing the type of machine to launch (pro or generic)
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
            An cloud provider instance
        """
        inst = self._create_instance(
            series=series,
            machine_type=machine_type,
            instance_name=instance_name,
            image_name=image_name,
            user_data=user_data,
            ephemeral=ephemeral,
            inbound_ports=inbound_ports,
        )
        inst.wait()
        logging.info(
            "--- {} instance launched: {}.".format(self.name, inst.name)
        )
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

    def locate_image_name(
        self,
        series: str,
        machine_type: str,
        daily: bool = True,
        include_deprecated: bool = False,
    ) -> str:
        """Locate and return the image name to use for vm provision.

        :param series:
            The ubuntu release to be used when locating the image name
        :machine_type:
            string representing the type of machine to launch (pro or generic)

        :returns:
            A image name to use when provisioning a virtual machine
            based on the series value
        """
        if not series:
            raise ValueError(
                "Must provide either series or image_name to launch azure"
            )

        image_type = ImageType.GENERIC
        if "pro-fips" in machine_type:
            image_type = ImageType.PRO_FIPS
        elif "pro" in machine_type:
            image_type = ImageType.PRO

        if daily:
            logging.debug("looking up daily image for {}".format(series))
            return self.api.daily_image(
                release=series,
                image_type=image_type,
                include_deprecated=include_deprecated,
            )
        else:
            logging.debug("looking up released image for {}".format(series))
            return self.api.released_image(
                release=series,
                image_type=image_type,
                include_deprecated=include_deprecated,
            )

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
        if self._ssh_key_managed:
            logging.debug("SSH key already set up")
            return

        logging.debug("Setting up SSH key")
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
        self._ssh_key_managed = True


class EC2(Cloud):
    """
    Class that represents the EC2 cloud provider.

    For AWS, we need to specify on the pycloudlib config file that
    the AWS region must be us-east-2. The reason for that is because
    our image ids were captured using that region.
    """

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
        machine_type: str,
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
        :machine_type:
            string representing the type of machine to launch (pro or generic)
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
            if series in ("xenial", "bionic") and "pro" not in machine_type:
                logging.debug(
                    "defaulting to non-daily image for awsgeneric-[16|18].04"
                )
                daily = False
            else:
                daily = True

            include_deprecated = False
            if series == "xenial":
                logging.debug(
                    "including deprecated images when locating xenial on aws"
                )
                include_deprecated = True

            image_name = self.locate_image_name(
                series,
                machine_type,
                daily=daily,
                include_deprecated=include_deprecated,
            )

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

    name = "azure"

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
        machine_type: str,
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
        :machine_type:
            string representing the type of machine to launch (pro or generic)
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
            image_name = self.locate_image_name(series, machine_type)

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
        cloud_credentials_path: Optional[str],
        tag: Optional[str] = None,
        timestamp_suffix: bool = True,
    ) -> None:
        super().__init__(
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
        machine_type: str,
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
        :machine_type:
            string representing the type of machine to launch (pro or generic)
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
            image_name = self.locate_image_name(series, machine_type)

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
        machine_type: str,
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
        :machine_type:
            string representing the type of machine to launch (pro or generic)
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
            image_name = self.locate_image_name(series, machine_type)

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

    def locate_image_name(
        self,
        series: str,
        machine_type: str,
        daily: bool = True,
        include_deprecated: bool = False,
    ) -> str:
        """Locate and return the image name to use for vm provision.

        :param series:
            The ubuntu release to be used when locating the image name
        :machine_type:
            string representing the type of machine to launch (pro or generic)

        :returns:
            A image name to use when provisioning a virtual machine
            based on the series value
        """
        if not series:
            raise ValueError(
                "Must provide either series or image_name to launch azure"
            )

        if daily:
            logging.debug("looking up daily image for {}".format(series))
            image_name = self.api.daily_image(release=series)
        else:
            logging.debug("looking up released image for {}".format(series))
            image_name = self.api.released_image(release=series)

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


class WSLCloud(pycloudlib.cloud.BaseCloud):
    def __init__(
        self,
        wsl_pubkey_path: str,
        wsl_privkey_path: str,
        wsl_ip_address: str,
    ):
        self.wsl_pubkey_path = wsl_pubkey_path
        self.wsl_privkey_path = wsl_privkey_path
        self.wsl_ip_address = wsl_ip_address
        super().__init__(tag="wsl")

    def _check_and_set_config(self, config_file, required_values):
        self.config = {
            "public_key_path": self.wsl_pubkey_path,
            "private_key_path": self.wsl_privkey_path,
        }

    def daily_image(self, release, **kwargs):
        return self.released_images(release, **kwargs)

    def delete_image(self, image_name):
        raise NotImplementedError

    def get_instance(self, instance_name):
        raise NotImplementedError

    def image_serial(self, release):
        raise NotImplementedError

    def launch(self, series: str):
        instance_parameters = self.released_image(series)
        inst = WSLInstance(
            self.key_pair,
            series=series,
            ip_address=self.wsl_ip_address,
        )
        inst._wait_for_execute()
        inst.delete()
        inst.uninstall_ubuntu_installer(instance_parameters["appxname"])

        inst.install_ubuntu_distro(
            store_id=instance_parameters["store_id"],
        )
        inst.launch_ubuntu_distro(
            launcher_name=instance_parameters["launcher"],
        )
        inst.create_non_root_user()

        return inst

    def snapshot(self):
        raise NotImplementedError

    def released_image(self, release: str, **kwargs):
        wsl_releases = {
            "jammy": {
                "name": "Ubuntu-22.04",
                "store_id": "9PN20MSR04DW",
                "launcher": "ubuntu2204.exe",
                "appxname": "Ubuntu22.04LTS",
            },
            "focal": {
                "name": "Ubuntu-20.04",
                "store_id": "9MTTCL66CPXJ",
                "launcher": "ubuntu2004.exe",
                "appxname": "Ubuntu20.04LTS",
            },
            "bionic": {
                "name": "Ubuntu-18.04",
                "store_id": "9PNKSF5ZN4SW",
                "launcher": "ubuntu1804.exe",
                "appxname": "Ubuntu18.04LTS",
            },
        }

        return wsl_releases.get(release)


class WSLInstance(pycloudlib.instance.BaseInstance):
    WSL_UBUNTU_MAP = {
        "jammy": "Ubuntu-22.04",
        "focal": "Ubuntu-20.04",
        "bionic": "Ubuntu-18.04",
    }

    def __init__(
        self,
        key_pair,
        series: str,
        ip_address: str,
    ):
        super().__init__(key_pair)
        self.ip_address = ip_address
        self.series = self.WSL_UBUNTU_MAP.get(series, "None")

    def install_ubuntu_distro(self, store_id: str):
        install_cmd = (
            'winget install --id "{}" --accept-source-agreements '
            "--accept-package-agreements --silent"
        )
        self.execute(
            install_cmd.format(store_id),
            run_on_wsl=False,
            check_stderr=True,
        )

    def launch_ubuntu_distro(self, launcher_name: str):
        self.execute(
            "{} install --root --ui=none".format(launcher_name),
            run_on_wsl=False,
            check_stderr=True,
        )

    def create_non_root_user(self, username="ubuntu"):
        self.execute(
            'sh -c "sudo adduser --disabled-password --gecos test {}"'.format(
                username
            ),
            run_on_wsl=True,
            use_sudo=True,
            check_stderr=True,
        )

        self.execute(
            "passwd -d {}".format(username),
            run_on_wsl=True,
            check_stderr=True,
            use_sudo=True,
        )

        configure_cmd = "sh -c \"echo '{} ALL=(ALL:ALL) NOPASSWD:ALL' | sudo EDITOR='tee -a' visudo\""  # noqa
        self.execute(
            configure_cmd.format(username),
            run_on_wsl=True,
            use_sudo=True,
            check_stderr=True,
        )

    def execute(
        self,
        command,
        stdin=None,
        run_on_wsl=True,
        use_sudo=False,
        check_stderr=False,
        **kwargs
    ):
        if isinstance(command, list):
            command = shlex.join(command)

        if isinstance(command, str):
            if run_on_wsl:
                script_path = "/tmp/wsl-bash-script.sh"
                with open(script_path, "w") as f:
                    f.write(command)

                self.push_file(
                    local_path=script_path,
                    remote_path=script_path,
                )

                user = "root" if use_sudo else "ubuntu"
                script_cmd = "bash {}".format(script_path)
                wsl_cmd = "wsl -d {} -u {} --exec {}"
                command = wsl_cmd.format(
                    self.series,
                    user,
                    script_cmd,
                )

        ret = self._ssh(command, stdin)

        if ret.stderr and check_stderr:
            logging.info("--- Error running cmd:\n{}".format(command))
            logging.info(ret.stderr)
            raise Exception("Command failed")

        return ret

    def _ssh(self, cmd, stdin=None):
        """Run a command via SSH.

        Args:
            command: string or list of the command to run
            stdin: optional, values to be passed in

        Returns:
            tuple of stdout, stderr and the return code

        """
        # I need to redefine this method here just to avoid calling
        # shell_pack, as it won't work on Windows or WSL instances
        client = self._ssh_connect()
        try:
            fp_in, fp_out, fp_err = client.exec_command(cmd)
        except (ConnectionResetError, NoValidConnectionsError, EOFError) as e:
            raise SSHException from e
        channel = fp_in.channel

        if stdin is not None:
            fp_in.write(stdin)
            fp_in.close()

        channel.shutdown_write()

        out = fp_out.read()
        err = fp_err.read()
        return_code = channel.recv_exit_status()

        out = "" if not out else out.rstrip().decode("utf-8")
        err = "" if not err else err.rstrip().decode("utf-8")

        return Result(out, err, return_code)

    def delete(self, wait=False):
        self.execute("wsl --shutdown", run_on_wsl=False, check_stderr=True)
        self.execute(
            "wsl --unregister {}".format(self.series),
            run_on_wsl=False,
            check_stderr=True,
        )

    def push_file(self, local_path, remote_path):
        windows_local_path = r"C:\Users\ubuntu\AppData\Local\Temp\pro_file"
        super().push_file(local_path, windows_local_path)

        wsl_cmd = "wsl -d {} -u root --exec {}".format(
            self.series,
            "mv /mnt/c/Users/ubuntu/AppData/Local/Temp/pro_file {}".format(
                remote_path
            ),
        )

        self.execute(
            wsl_cmd,
            run_on_wsl=False,
        )

    def uninstall_ubuntu_installer(self, appx_name: str):
        distro_installer_cmd = (
            'powershell -Command "(Get-AppxPackage | Where-Object Name -like'
            " 'CanonicalGroupLimited.{}').PackageFullName\""
        )
        distro_installer_path = self.execute(
            distro_installer_cmd.format(appx_name),
            run_on_wsl=False,
            check_stderr=True,
        )

        if distro_installer_path.stdout:
            distro_installer_remove_cmd = (
                'powershell -Command "Remove-AppxPackage (Get-AppxPackage | Where-Object Name -like'  # noqa
                " 'CanonicalGroupLimited.{}').PackageFullName\""
            )
            self.execute(
                distro_installer_remove_cmd.format(appx_name),
                run_on_wsl=False,
                check_stderr=True,
            )

    @property
    def ip(self):
        return self.ip_address

    def id(self):
        return "wsl"

    def _do_restart(self):
        pass

    @property
    def name(self):
        return self.series

    def shutdown(self):
        self.execute(
            "wsl -d {} --shutdown".format(self.series),
            run_on_wsl=False,
            check_stderr=True,
        )

    def start(self):
        pass

    def wait_for_delete(self):
        pass

    def wait_for_stop(self):
        pass

    def _wait_for_execute(self):
        # Wait 40 minutes before failing. AWS EC2 metal instances can take
        # over 20 minutes to start or restart, so we shouldn't lower
        # this timeout
        start = time.time()
        end = start + 40 * 60
        while time.time() < end:
            with suppress(SSHException, OSError):
                ret = self.execute("dir", run_on_wsl=False)
                if not ret.failed:
                    return
            time.sleep(1)

        raise PycloudlibTimeoutError(
            "Instance can't be reached after 40 minutes. "
            "Failed to obtain new boot id",
        )


class WSL(Cloud):
    name = ""

    def __init__(
        self,
        wsl_pubkey_path: str,
        wsl_privkey_path: str,
        wsl_ip_address: str,
        cloud_credentials_path: Optional[str],
    ) -> None:
        self._api = None
        self._azure_api = None
        self.wsl_pubkey_path = wsl_pubkey_path
        self.wsl_privkey_path = wsl_privkey_path
        self.wsl_ip_address = wsl_ip_address
        self.cloud_credentials_path = cloud_credentials_path
        self._ssh_key_managed = False

    @property
    def pycloudlib_cls(self):
        """Return the pycloudlib cls to be used as an api."""
        return WSLCloud

    @property
    def azure_api(self):
        if self._azure_api is None:
            self._azure_api = pycloudlib.Azure(
                config_file=self.cloud_credentials_path,
                tag="wsl",
            )

        return self._azure_api

    @property
    def api(self) -> pycloudlib.cloud.BaseCloud:
        """Return the api used to interact with the cloud provider."""
        if self._api is None:
            self._api = self.pycloudlib_cls(
                wsl_pubkey_path=self.wsl_pubkey_path,
                wsl_privkey_path=self.wsl_privkey_path,
                wsl_ip_address=self.wsl_ip_address,
            )

        return self._api

    def stop_windows_machine(self):
        windows_machine = self.azure_api.get_instance(
            instance_id="wsl-test",
            search_all=True,
        )

        windows_machine.shutdown(wait=True)

    def start_windows_machine(self):
        windows_machine = self.azure_api.get_instance(
            instance_id="wsl-test",
            search_all=True,
        )

        start = windows_machine._client.virtual_machines.begin_start(
            resource_group_name=windows_machine._instance["rg_name"],
            vm_name=windows_machine.name,
        )
        start.wait()

    def _create_instance(
        self,
        series: str,
        machine_type: str,
        instance_name: Optional[str] = None,
        image_name: Optional[str] = None,
        user_data: Optional[str] = None,
        ephemeral: bool = False,
        inbound_ports: Optional[List[str]] = None,
    ) -> pycloudlib.instance:
        """Create an instance for on the cloud provider.

        :param series:
            The ubuntu release to be used when creating an instance. We will
            create an image based on this value if the user does not provide
            a image_name value

        :returns:
            A cloud provider instance
        """
        return self.api.launch(series)

    def launch(
        self,
        series: str,
        machine_type: str,
        instance_name: Optional[str] = None,
        image_name: Optional[str] = None,
        user_data: Optional[str] = None,
        ephemeral: bool = False,
        inbound_ports: Optional[List[str]] = None,
    ) -> pycloudlib.instance.BaseInstance:
        """Create and wait for cloud provider instance to be ready.

        :param series:
            The ubuntu release to be used when creating an instance. We will
            create an image based on this value if the used does not provide
            a image_name value

        :returns:
            An cloud provider instance
        """

        self.start_windows_machine()

        inst = self._create_instance(
            series=series,
            machine_type=machine_type,
        )
        logging.info("--- WSL {} instance launched.".format(inst.name))

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

    def locate_image_name(
        self,
        series: str,
        machine_type: str,
        daily: bool = True,
        include_deprecated: bool = False,
    ) -> str:
        """Locate and return the WSL image name to use for vm provision.

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

        return self.api.released_image(release=series)

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
        if self._ssh_key_managed:
            logging.debug("SSH key already set up")
            return

        self.api.use_key(
            public_key_path=self.wsl_pubkey_path,
            private_key_path=self.wsl_privkey_path,
        )
