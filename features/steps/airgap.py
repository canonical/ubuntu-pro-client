import os
import re
from typing import Any, Dict  # noqa: F401

import yaml
from behave import when

from features.steps.files import when_i_create_file_with_content
from features.steps.shell import when_i_run_command


@when("I download the service credentials on the `{machine_name}` machine")
def download_service_credentials(context, machine_name):
    token = context.pro_config.contract_token
    when_i_run_command(
        context,
        "get-resource-tokens {}".format(token),
        "as non-root",
        machine_name=machine_name,
    )

    context.service_credentials = context.process.stdout


@when(
    "I extract the `{service}` credentials from the `{machine_name}` machine"
)
def extract_service_credentials(context, service, machine_name):
    if getattr(context, "service_mirror_cfg", None) is None:
        context.service_mirror_cfg = {}
    credentials_pattern = r"{}:\s+(.+)".format(service)
    credentials_match = re.search(
        credentials_pattern, context.service_credentials
    )
    if credentials_match:
        extracted_credentials = credentials_match.group(1)
        context.service_mirror_cfg[service.replace("-", "_")] = {
            "credentials": extracted_credentials
        }


@when(
    "I set the apt-mirror file for `{release}` with the `{service_list}` credentials on the `{machine_name}` machine"  # noqa
)
def set_apt_mirror_file_with_credentials(
    context, release, service_list, machine_name
):
    service_list = service_list.split(",")

    apt_mirror_file = """
    set nthreads     20
    set _tilde 0
    """

    for service in service_list:
        token = context.service_mirror_cfg[service.replace("-", "_")][
            "credentials"
        ]
        service_type = service.split("-")[1]

        apt_mirror_cfg = """
        deb https://bearer:{}@esm.ubuntu.com/{}/ubuntu/ jammy-{}-updates main
        deb https://bearer:{}@esm.ubuntu.com/{}/ubuntu/ jammy-{}-security main
        """.format(
            token,
            service_type,
            service_type,
            token,
            service_type,
            service_type,
        )

        apt_mirror_file += "\n" + apt_mirror_cfg + "\n"
        context.service_mirror_cfg[service.replace("-", "_")]["path"] = (
            "/var/spool/apt-mirror/mirror/esm.ubuntu.com/{}/".format(
                service_type
            )
        )

    apt_mirror_file += "clean http://archive.ubuntu.com/ubuntu"

    context.text = apt_mirror_file.strip()
    when_i_create_file_with_content(
        context,
        "/etc/apt/mirror.list",
        machine_name=machine_name,
    )


@when(
    "I serve the `{service}` mirror using port `{port}` on the `{machine_name}` machine"  # noqa
)
def serve_apt_mirror(context, service, port, machine_name):
    service_type = service.replace("-", "_")
    path = context.service_mirror_cfg[service_type]["path"]
    cmd = "nohup sh -c 'python3 -m http.server --directory {} {} > /dev/null 2>&1 &'".format(  # noqa
        path, port
    )

    when_i_run_command(
        context,
        cmd,
        "with sudo",
        machine_name=machine_name,
    )

    if service_type in context.service_mirror_cfg:
        context.service_mirror_cfg[service_type]["port"] = port


@when(
    "I create the contract config overrides file for `{service_list}` on the `{machine_name}` machine"  # noqa
)
def create_contract_overrides(context, service_list, machine_name):
    token = context.pro_config.contract_token
    config_override = {token: {}}  # type: Dict[str, Any]

    for service in service_list.split(","):
        config_override[token][service] = {
            "directives": {
                "aptURL": "http://{}:{}".format(
                    context.machines[machine_name].instance.ip,
                    context.service_mirror_cfg.get(
                        service.replace("-", "_"), {}
                    ).get("port", "8000"),
                )
            }
        }

    context.text = yaml.dump(config_override)
    contract_override_path = "/tmp/contract-override"
    when_i_create_file_with_content(
        context,
        contract_override_path,
        machine_name=machine_name,
    )

    context.service_mirror_cfg["contract_override"] = contract_override_path


@when(
    "I generate the contracts-airgapped configuration on the `{machine_name}` machine"  # noqa
)
def i_configure_the_ua_airgapped_service(context, machine_name):
    contract_override_path = context.service_mirror_cfg["contract_override"]
    contract_final_cfg_path = "contract-server-ready.yml"
    cmd = "sh -c 'cat {} | pro-airgapped > {}'".format(
        contract_override_path,
        contract_final_cfg_path,
    )

    when_i_run_command(
        context,
        cmd,
        "with sudo",
        machine_name=machine_name,
    )

    context.service_mirror_cfg["contract_final_cfg"] = contract_final_cfg_path


@when(
    "I send the contracts-airgapped config from the `{base_machine}` machine to the `{target_machine}` machine"  # noqa
)
def i_fetch_contracts_airgapped_config(context, base_machine, target_machine):
    local_file_path = "/tmp/contracts-airgapped-cfg"

    context.machines[base_machine].instance.pull_file(
        context.service_mirror_cfg["contract_final_cfg"],
        local_file_path,
    )

    context.machines[target_machine].instance.push_file(
        local_file_path,
        context.service_mirror_cfg["contract_final_cfg"],
    )

    os.unlink(local_file_path)


@when(
    "I start the contracts-airgapped service on the `{machine_name}` machine"
)
def i_start_the_contracts_airgapped_service(context, machine_name):
    path = context.service_mirror_cfg["contract_final_cfg"]
    cmd = "nohup sh -c 'contracts-airgapped --input=./{} > /dev/null 2>&1 &'".format(  # noqa
        path
    )

    when_i_run_command(context, cmd, "with sudo", machine_name=machine_name)


@when(
    "I consolidate `{services_list}` on a single mirror on the `{machine_name}` machine"  # noqa
)  # noqa
def then_i_consolidate_services_on_the_same_mirror(
    context, services_list, machine_name
):
    services = services_list.split(",")
    all_mirrors_path = "/var/spool/apt-mirror/mirror/all-mirrors/"

    for service in services:
        cmd = "rsync -a /var/spool/apt-mirror/mirror/esm.ubuntu.com/{}/ {}".format(  # noqa
            service.split("-")[1], all_mirrors_path
        )
        when_i_run_command(
            context, cmd, "with sudo", machine_name=machine_name
        )

    context.service_mirror_cfg["all_mirrors"] = {"path": all_mirrors_path}
