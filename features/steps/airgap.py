import json
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
    all_mirrors_path = "/var/spool/ditto-repo/all-mirrors/"

    for service in services:
        cmd = "rsync -a /var/spool/ditto-repo/{}/ {}".format(  # noqa
            service.split("-")[1], all_mirrors_path
        )
        when_i_run_command(
            context, cmd, "with sudo", machine_name=machine_name
        )

    context.service_mirror_cfg["all_mirrors"] = {"path": all_mirrors_path}


@when(
    "I set the ditto-repo config file for `{release}` with the `{service_list}` credentials on the `{machine_name}` machine"  # noqa
)
def set_ditto_repo_config_with_credentials(
    context, release, service_list, machine_name
):
    """
    Generate ditto-repo configuration JSON files with credentials for ESM services.
    Creates separate config files for both 'updates' and 'security' distributions.
    Similar to set_apt_mirror_file_with_credentials but for ditto-repo tool.
    """
    service_list = service_list.split(",")

    if not hasattr(context, "ditto_config_files"):
        context.ditto_config_files = {}

    for service in service_list:
        token = context.service_mirror_cfg[service.replace("-", "_")][
            "credentials"
        ]
        service_type = service.split("-")[1]

        # Create authenticated URL for ditto-repo
        repo_url = "https://bearer:{}@esm.ubuntu.com/{}/ubuntu/".format(
            token, service_type
        )

        # Create two configs: one for updates, one for security
        for dist_suffix in ["updates", "security"]:
            ditto_config = {
                "repo-url": repo_url,
                "dist": "{}-{}-{}".format(release, service_type, dist_suffix),
                "components": ["main"],
                "archs": ["amd64"],
                "languages": ["en"],
                "download-path": "/var/spool/ditto-repo/{}/ubuntu/".format(
                    service_type,
                ),
                "workers": 5,
            }

            # Write config to file
            text = json.dumps(ditto_config, indent=4)
            config_file_path = "/etc/ditto-config-{}-{}.json".format(
                service_type, dist_suffix
            )
            when_i_create_file_with_content(
                context,
                config_file_path,
                machine_name=machine_name,
                text=text,
            )

            # Store config file paths for later use
            config_key = "{}_{}".format(service_type, dist_suffix)
            context.ditto_config_files[config_key] = config_file_path

        # Store the base download path for later use
        context.service_mirror_cfg[service.replace("-", "_")]["path"] = (
            "/var/spool/ditto-repo/{}/".format(service_type)
        )


@when(
    "I download the ditto binary from `{url}` on the `{machine_name}` machine"
)
def download_ditto_binary(context, url, machine_name):
    """
    Download the ditto-repo binary from a configurable URL and make it executable.
    """
    ditto_binary_path = "/usr/local/bin/ditto"

    # Download the binary using wget
    download_cmd = "wget -O {} {}".format(ditto_binary_path, url)
    when_i_run_command(
        context,
        download_cmd,
        "with sudo",
        machine_name=machine_name,
    )

    # Make the binary executable
    chmod_cmd = "chmod +x {}".format(ditto_binary_path)
    when_i_run_command(
        context,
        chmod_cmd,
        "with sudo",
        machine_name=machine_name,
    )

    # Store the binary path in context for later use
    if not hasattr(context, "ditto_binary_path"):
        context.ditto_binary_path = ditto_binary_path


@when(
    "I run ditto with the `{config_key}` config on the `{machine_name}` machine"  # noqa
)
def run_ditto_with_config(context, config_key, machine_name):
    """
    Run the ditto command with a specified config file.
    Copies the config file to ditto-config.json in a working directory.
    """
    # Get the config file path from context
    if not hasattr(context, "ditto_config_files"):
        raise ValueError("No ditto config files found in context")

    if config_key not in context.ditto_config_files:
        raise ValueError(
            "Config key '{}' not found. Available keys: {}".format(
                config_key, list(context.ditto_config_files.keys())
            )
        )

    source_config_path = context.ditto_config_files[config_key]

    # Copy the config file to ditto-config.json in the working directory
    target_config_path = "ditto-config.json"
    cp_cmd = "cp {} {}".format(source_config_path, target_config_path)
    when_i_run_command(
        context,
        cp_cmd,
        "with sudo",
        machine_name=machine_name,
    )

    # Run ditto from the working directory
    ditto_cmd = "ditto"
    when_i_run_command(
        context,
        ditto_cmd,
        "with sudo",
        machine_name=machine_name,
    )
