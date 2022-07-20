import datetime
import json
import logging
import re
from functools import lru_cache
from typing import Any, Dict, List, Optional, Tuple

from uaclient import (
    apt,
    event_logger,
    exceptions,
    messages,
    serviceclient,
    snap,
    system,
    util,
)
from uaclient.entitlements.base import IncompatibleService, UAEntitlement
from uaclient.entitlements.entitlement_status import ApplicationStatus
from uaclient.files import state_files
from uaclient.types import StaticAffordance

LIVEPATCH_RETRIES = [0.5, 1.0]
HTTP_PROXY_OPTION = "http-proxy"
HTTPS_PROXY_OPTION = "https-proxy"

ERROR_MSG_MAP = {
    "Unknown Auth-Token": "Invalid Auth-Token provided to livepatch.",
    "unsupported kernel": "Your running kernel is not supported by Livepatch.",
}

LIVEPATCH_CMD = "/snap/bin/canonical-livepatch"

LIVEPATCH_API_V1_KERNELS_SUPPORTED = "/v1/api/kernels/supported"

event = event_logger.get_event_logger()


class UALivepatchClient(serviceclient.UAServiceClient):

    cfg_url_base_attr = "livepatch_url"
    api_error_cls = exceptions.UrlError

    def is_kernel_supported(
        self, version: str, flavor: str, arch: str, codename: str
    ) -> Optional[bool]:
        """
        :returns: True if supported
                  False if unsupported
                  None if API returns error or ambiguous response
        """
        query_params = {
            "kernel-version": version,
            "flavour": flavor,
            "architecture": arch,
            "codename": codename,
        }
        headers = self.headers()
        try:
            result, _headers = self.request_url(
                LIVEPATCH_API_V1_KERNELS_SUPPORTED,
                query_params=query_params,
                headers=headers,
            )
        except Exception as e:
            with util.disable_log_to_console():
                logging.warning(
                    "error while checking livepatch supported kernels API"
                )
                logging.warning(e)
            return None

        if not isinstance(result, dict):
            return None

        return bool(result.get("Supported", False))


def _on_supported_kernel_cli() -> Optional[bool]:
    if is_livepatch_installed():
        try:
            out, _ = system.subp([LIVEPATCH_CMD, "status", "--format", "json"])
        except exceptions.ProcessExecutionError:
            logging.warning(
                "canonical-livepatch returned error when "
                "checking kernel support"
            )
            return None

        cli_statuses = json.loads(out).get("Status", [])
        if len(cli_statuses) > 0:
            cli_status = cli_statuses[0]

            cli_supported = cli_status.get("Supported", None)
            if cli_supported == "supported":
                return True
            if cli_supported == "unsupported":
                return False

    return None


def _on_supported_kernel_cache(
    version: str, flavor: str, arch: str, codename: str
) -> Tuple[bool, Optional[bool]]:
    """Check local cache of kernel support

    :return: (is_cache_valid, result)
    """
    try:
        cache_data = state_files.livepatch_support_cache.read()
    except Exception:
        cache_data = None

    if cache_data is not None:
        one_week_ago = datetime.datetime.now(
            datetime.timezone.utc
        ) - datetime.timedelta(days=7)
        if all(
            [
                cache_data.cached_at > one_week_ago,  # less than one week old
                cache_data.version == version,
                cache_data.flavor == flavor,
                cache_data.arch == arch,
                cache_data.codename == codename,
            ]
        ):
            if cache_data.supported is None:
                with util.disable_log_to_console():
                    logging.warning(
                        "livepatch kernel support cache has None value"
                    )
            return (True, cache_data.supported)
    return (False, None)


def _on_supported_kernel_api(
    version: str, flavor: str, arch: str, codename: str
) -> Optional[bool]:
    supported = UALivepatchClient().is_kernel_supported(
        version=version,
        flavor=flavor,
        arch=arch,
        codename=codename,
    )

    # cache response before returning
    state_files.livepatch_support_cache.write(
        state_files.LivepatchSupportCacheData(
            version=version,
            flavor=flavor,
            arch=arch,
            codename=codename,
            supported=supported,
            cached_at=datetime.datetime.now(datetime.timezone.utc),
        )
    )

    if supported is None:
        with util.disable_log_to_console():
            logging.warning(
                "livepatch kernel support API response was ambiguous"
            )
    return supported


@lru_cache(maxsize=None)
def on_supported_kernel() -> Optional[bool]:
    """
    Checks CLI, local cache, and API in that order for kernel support
    If all checks fail to return an authoritative answer, we return None
    """

    # first check cli
    cli_says = _on_supported_kernel_cli()
    if cli_says is not None:
        logging.debug("using livepatch cli for support")
        return cli_says

    # gather required system info to query support
    kernel_info = system.get_kernel_info()
    if (
        kernel_info.flavor is None
        or kernel_info.major is None
        or kernel_info.minor is None
    ):
        logging.warning(
            "unable to determine enough kernel information to "
            "check livepatch support"
        )
        return None

    arch = util.standardize_arch_name(system.get_lscpu_arch())
    codename = system.get_platform_info()["series"]

    lp_api_kernel_ver = "{major}.{minor}".format(
        major=kernel_info.major, minor=kernel_info.minor
    )

    # second check cache
    is_cache_valid, cache_says = _on_supported_kernel_cache(
        lp_api_kernel_ver, kernel_info.flavor, arch, codename
    )
    if is_cache_valid:
        logging.debug("using livepatch support cache")
        return cache_says

    # finally check api
    logging.debug("using livepatch support api")
    return _on_supported_kernel_api(
        lp_api_kernel_ver, kernel_info.flavor, arch, codename
    )


def unconfigure_livepatch_proxy(
    protocol_type: str, retry_sleeps: Optional[List[float]] = None
) -> None:
    """
    Unset livepatch configuration settings for http and https proxies.

    :param protocol_type: String either http or https
    :param retry_sleeps: Optional list of sleep lengths to apply between
        retries. Specifying a list of [0.5, 1] tells subp to retry twice
        on failure; sleeping half a second before the first retry and 1 second
        before the second retry.
    """
    if not is_livepatch_installed():
        return
    system.subp(
        [LIVEPATCH_CMD, "config", "{}-proxy=".format(protocol_type)],
        retry_sleeps=retry_sleeps,
    )


def configure_livepatch_proxy(
    http_proxy: Optional[str] = None,
    https_proxy: Optional[str] = None,
    retry_sleeps: Optional[List[float]] = None,
) -> None:
    """
    Configure livepatch to use http and https proxies.

    :param http_proxy: http proxy to be used by livepatch. If None, it will
                       not be configured
    :param https_proxy: https proxy to be used by livepatch. If None, it will
                        not be configured
    :@param retry_sleeps: Optional list of sleep lengths to apply between
                               snap calls
    """
    if http_proxy or https_proxy:
        event.info(
            messages.SETTING_SERVICE_PROXY.format(
                service=LivepatchEntitlement.title
            )
        )

    if http_proxy:
        system.subp(
            [LIVEPATCH_CMD, "config", "http-proxy={}".format(http_proxy)],
            retry_sleeps=retry_sleeps,
        )

    if https_proxy:
        system.subp(
            [LIVEPATCH_CMD, "config", "https-proxy={}".format(https_proxy)],
            retry_sleeps=retry_sleeps,
        )


def get_config_option_value(key: str) -> Optional[str]:
    """
    Gets the config value from livepatch.
    :param key: can be any valid livepatch config option
    :return: the value of the livepatch config option, or None if not set
    """
    out, _ = system.subp([LIVEPATCH_CMD, "config"])
    match = re.search("^{}: (.*)$".format(key), out, re.MULTILINE)
    value = match.group(1) if match else None
    if value:
        # remove quotes if present
        value = re.sub(r"\"(.*)\"", r"\g<1>", value)
    return value.strip() if value else None


def is_livepatch_installed() -> bool:
    return system.which(LIVEPATCH_CMD) is not None


class LivepatchEntitlement(UAEntitlement):

    help_doc_url = "https://ubuntu.com/security/livepatch"
    name = "livepatch"
    title = "Livepatch"
    description = "Canonical Livepatch service"
    affordance_check_arch = False
    affordance_check_series = False
    affordance_check_kernel_min_version = False
    affordance_check_kernel_flavor = False

    @property
    def incompatible_services(self) -> Tuple[IncompatibleService, ...]:
        from uaclient.entitlements.fips import FIPSEntitlement
        from uaclient.entitlements.realtime import RealtimeKernelEntitlement

        return (
            IncompatibleService(
                FIPSEntitlement, messages.LIVEPATCH_INVALIDATES_FIPS
            ),
            IncompatibleService(
                RealtimeKernelEntitlement,
                messages.REALTIME_LIVEPATCH_INCOMPATIBLE,
            ),
        )

    @property
    def static_affordances(self) -> Tuple[StaticAffordance, ...]:
        # Use a lambda so we can mock system.is_container in tests
        from uaclient.entitlements.fips import FIPSEntitlement

        fips_ent = FIPSEntitlement(self.cfg)

        is_fips_enabled = bool(
            fips_ent.application_status()[0] == ApplicationStatus.ENABLED
        )

        return (
            (
                messages.LIVEPATCH_ERROR_INSTALL_ON_CONTAINER,
                lambda: system.is_container(),
                False,
            ),
            (
                messages.LIVEPATCH_ERROR_WHEN_FIPS_ENABLED,
                lambda: is_fips_enabled,
                False,
            ),
        )

    def _perform_enable(self, silent: bool = False) -> bool:
        """Enable specific entitlement.

        @return: True on success, False otherwise.
        """
        if not system.which(snap.SNAP_CMD):
            event.info("Installing snapd")
            event.info(messages.APT_UPDATING_LISTS)
            try:
                apt.run_apt_update_command()
            except exceptions.UserFacingError as e:
                logging.debug(
                    "Trying to install snapd."
                    " Ignoring apt-get update failure: %s",
                    str(e),
                )
            try:
                system.subp(
                    ["apt-get", "install", "--assume-yes", "snapd"],
                    retry_sleeps=apt.APT_RETRIES,
                )
            except exceptions.ProcessExecutionError:
                raise exceptions.CannotInstallSnapdError()

        elif not snap.is_installed():
            raise exceptions.SnapdNotProperlyInstalledError(
                snap_cmd=snap.SNAP_CMD, service=self.title
            )

        try:
            system.subp(
                [snap.SNAP_CMD, "wait", "system", "seed.loaded"], capture=True
            )
        except exceptions.ProcessExecutionError as e:
            if re.search(r"unknown command .*wait", str(e).lower()):
                logging.warning(messages.SNAPD_DOES_NOT_HAVE_WAIT_CMD)
            else:
                raise

        http_proxy = util.validate_proxy(
            "http", self.cfg.http_proxy, util.PROXY_VALIDATION_SNAP_HTTP_URL
        )
        https_proxy = util.validate_proxy(
            "https", self.cfg.https_proxy, util.PROXY_VALIDATION_SNAP_HTTPS_URL
        )
        snap.configure_snap_proxy(
            http_proxy=http_proxy,
            https_proxy=https_proxy,
            retry_sleeps=snap.SNAP_INSTALL_RETRIES,
        )

        if not is_livepatch_installed():
            event.info("Installing canonical-livepatch snap")
            try:
                system.subp(
                    [snap.SNAP_CMD, "install", "canonical-livepatch"],
                    capture=True,
                    retry_sleeps=snap.SNAP_INSTALL_RETRIES,
                )
            except exceptions.ProcessExecutionError as e:
                raise exceptions.ErrorInstallingLivepatch(error_msg=str(e))

        configure_livepatch_proxy(http_proxy, https_proxy)

        return self.setup_livepatch_config(
            process_directives=True, process_token=True
        )

    def setup_livepatch_config(
        self, process_directives: bool = True, process_token: bool = True
    ) -> bool:
        """Processs configuration setup for livepatch directives.

        :param process_directives: Boolean set True when directives should be
            processsed.
        :param process_token: Boolean set True when token should be
            processsed.
        """
        entitlement_cfg = self.cfg.machine_token_file.entitlements.get(
            self.name
        )
        if process_directives:
            try:
                process_config_directives(entitlement_cfg)
            except exceptions.ProcessExecutionError as e:
                msg = "Unable to configure Livepatch: " + str(e)
                event.info(msg)
                logging.error(msg)
                return False
        if process_token:
            livepatch_token = entitlement_cfg.get("resourceToken")
            if not livepatch_token:
                logging.debug(
                    "No specific resourceToken present. Using machine token as"
                    " %s credentials",
                    self.title,
                )
                livepatch_token = self.cfg.machine_token["machineToken"]
            application_status, _details = self.application_status()
            if application_status != ApplicationStatus.DISABLED:
                logging.info(
                    "Disabling %s prior to re-attach with new token",
                    self.title,
                )
                try:
                    system.subp([LIVEPATCH_CMD, "disable"])
                except exceptions.ProcessExecutionError as e:
                    logging.error(str(e))
                    return False
            try:
                system.subp(
                    [LIVEPATCH_CMD, "enable", livepatch_token], capture=True
                )
            except exceptions.ProcessExecutionError as e:
                msg = "Unable to enable Livepatch: "
                for error_message, print_message in ERROR_MSG_MAP.items():
                    if error_message in str(e):
                        msg += print_message
                        break
                if msg == "Unable to enable Livepatch: ":
                    msg += str(e)
                event.info(msg)
                return False
            event.info("Canonical livepatch enabled.")
        return True

    def _perform_disable(self, silent=False):
        """Disable specific entitlement

        @return: True on success, False otherwise.
        """
        if not is_livepatch_installed():
            return True
        system.subp([LIVEPATCH_CMD, "disable"], capture=True)
        return True

    def application_status(
        self,
    ) -> Tuple[ApplicationStatus, Optional[messages.NamedMessage]]:
        status = (ApplicationStatus.ENABLED, None)

        if not is_livepatch_installed():
            return (ApplicationStatus.DISABLED, messages.LIVEPATCH_NOT_ENABLED)

        try:
            system.subp(
                [LIVEPATCH_CMD, "status"], retry_sleeps=LIVEPATCH_RETRIES
            )
        except exceptions.ProcessExecutionError as e:
            # TODO(May want to parse INACTIVE/failure assessment)
            logging.debug("Livepatch not enabled. %s", str(e))
            return (
                ApplicationStatus.DISABLED,
                messages.NamedMessage(name="", msg=str(e)),
            )
        return status

    def enabled_warning_status(
        self,
    ) -> Tuple[bool, Optional[messages.NamedMessage]]:
        if on_supported_kernel() is False:
            kernel_info = system.get_kernel_info()
            arch = system.get_lscpu_arch()
            return (
                True,
                messages.LIVEPATCH_KERNEL_NOT_SUPPORTED.format(
                    version=kernel_info.uname_release, arch=arch
                ),
            )
        # is on_supported_kernel returns None we default to no warning
        # because there would be no way for a user to resolve the warning
        return False, None

    def status_description_override(self):
        if on_supported_kernel() is False and not system.is_container():
            return messages.LIVEPATCH_KERNEL_NOT_SUPPORTED_DESCRIPTION
        return None

    def process_contract_deltas(
        self,
        orig_access: Dict[str, Any],
        deltas: Dict[str, Any],
        allow_enable: bool = False,
    ) -> bool:
        """Process any contract access deltas for this entitlement.

        :param orig_access: Dictionary containing the original
            resourceEntitlement access details.
        :param deltas: Dictionary which contains only the changed access keys
        and values.
        :param allow_enable: Boolean set True if allowed to perform the enable
            operation. When False, a message will be logged to inform the user
            about the recommended enabled service.

        :return: True when delta operations are processed; False when noop.
        """
        if super().process_contract_deltas(orig_access, deltas, allow_enable):
            return True  # Already processed parent class deltas

        delta_entitlement = deltas.get("entitlement", {})
        process_enable_default = delta_entitlement.get("obligations", {}).get(
            "enabledByDefault", False
        )

        if process_enable_default:
            enable_success, _ = self.enable()
            return enable_success

        application_status, _ = self.application_status()
        if application_status == ApplicationStatus.DISABLED:
            return False  # only operate on changed directives when ACTIVE
        delta_directives = delta_entitlement.get("directives", {})
        supported_deltas = set(["caCerts", "remoteServer"])
        process_directives = bool(
            supported_deltas.intersection(delta_directives)
        )
        process_token = bool(deltas.get("resourceToken", False))
        if any([process_directives, process_token]):
            logging.info("Updating '%s' on changed directives.", self.name)
            return self.setup_livepatch_config(
                process_directives=process_directives,
                process_token=process_token,
            )
        return True


def process_config_directives(cfg):
    """Process livepatch configuration directives.

    We process caCerts before remoteServer because changing remote-server
    in the canonical-livepatch CLI performs a PUT against the new server name.
    If new caCerts were required for the new remoteServer, this
    canonical-livepatch client PUT could fail on unmatched old caCerts.

    @raises: ProcessExecutionError if unable to configure livepatch.
    """
    if not cfg:
        return
    directives = cfg.get("entitlement", {}).get("directives", {})
    ca_certs = directives.get("caCerts")
    if ca_certs:
        system.subp(
            [LIVEPATCH_CMD, "config", "ca-certs={}".format(ca_certs)],
            capture=True,
        )
    remote_server = directives.get("remoteServer", "")
    if remote_server.endswith("/"):
        remote_server = remote_server[:-1]
    if remote_server:
        system.subp(
            [
                LIVEPATCH_CMD,
                "config",
                "remote-server={}".format(remote_server),
            ],
            capture=True,
        )
