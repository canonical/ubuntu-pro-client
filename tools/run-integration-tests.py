import os
import subprocess
import tarfile
import time
from datetime import datetime
from sys import stdout

import click
import yaml

SERIES_TO_VERSION = {
    "xenial": "16.04",
    "bionic": "18.04",
    "focal": "20.04",
    "jammy": "22.04",
    "mantic": "23.10",
}

TOKEN_TO_ENVVAR = {
    "prod": "UACLIENT_BEHAVE_CONTRACT_TOKEN",
    "staging": "UACLIENT_BEHAVE_CONTRACT_TOKEN_STAGING",
    "expired": "UACLIENT_BEHAVE_CONTRACT_TOKEN_STAGING_EXPIRED",
}

PLATFORM_SERIES_TESTS = {
    "aws.generic": ["xenial", "bionic", "focal", "jammy"],
    "aws.pro": ["xenial", "bionic", "focal", "jammy"],
    "aws.pro-fips": ["xenial", "bionic", "focal"],
    "azure.generic": ["xenial", "bionic", "focal", "jammy", "mantic"],
    "azure.pro": ["xenial", "bionic", "focal", "jammy"],
    "azure.pro-fips": ["xenial", "bionic", "focal"],
    "gcp.generic": ["xenial", "bionic", "focal", "jammy", "mantic"],
    "gcp.pro": ["xenial", "bionic", "focal", "jammy"],
    "gcp.pro-fips": ["bionic", "focal"],
    "lxd-container": ["xenial", "bionic", "focal", "jammy", "mantic"],
    "lxd-vm": ["xenial", "bionic", "focal", "jammy", "mantic"],
    "docker": ["focal"],
    "upgrade": ["xenial", "bionic", "focal", "jammy", "mantic"],
}

PLATFORM_ARGS = {
    "aws.generic": ["-D", "machine_types=aws.generic"],
    "aws.pro": ["-D", "machine_types=aws.pro"],
    "aws.pro-fips": ["-D", "machine_types=aws.pro-fips"],
    "azure.generic": ["-D", "machine_types=azure.generic"],
    "azure.pro": ["-D", "machine_types=azure.pro"],
    "azure.pro-fips": ["-D", "machine_types=azure.pro-fips"],
    "gcp.generic": ["-D", "machine_types=gcp.generic"],
    "gcp.pro": ["-D", "machine_types=gcp.pro"],
    "gcp.pro-fips": ["-D", "machine_types=gcp.pro-fips"],
    "lxd-container": ["-D", "machine_types=lxd-container", "--tags=-upgrade"],
    "lxd-vm": ["-D", "machine_types=lxd-vm", "--tags=-docker"],
    "docker": ["--tags=docker", "features/docker.feature"],
    "upgrade": ["--tags=upgrade"],
}


def is_compatible(platform, series):
    return series in PLATFORM_SERIES_TESTS[platform]


def build_commands(
    platform, series, install_from, check_version, token, credentials_path, wip
):
    with open(credentials_path) as f:
        credentials = yaml.safe_load(f)
    commands = []
    for p in platform:
        for s in series:
            # Not all tests can run in all platforms
            if is_compatible(p, s):
                series_version = SERIES_TO_VERSION[s]
                env = os.environ.copy()

                # Inject tokens from credentials
                for t in token:
                    envvar = TOKEN_TO_ENVVAR[t]
                    env[envvar] = credentials["token"].get(envvar)

                # Tox command itself
                command = [
                    "tox",
                    "-e",
                    "behave",
                    "--",
                    "-D",
                    "install_from={}".format(install_from),
                    "-D",
                    "releases={}".format(s),
                    *PLATFORM_ARGS[p],
                ]

                if check_version:
                    command.extend(
                        [
                            "-D",
                            "check_version={}~{}".format(
                                check_version,
                                series_version,
                            ),
                        ]
                    )

                # Wip
                if wip:
                    command.extend(["--tags=wip", "--stop"])

                commands.append(
                    (
                        "behave-{}-{}".format(p.replace(".", "-"), s),
                        command,
                        env,
                    )
                )

    return commands


@click.command()
@click.option(
    "-p",
    "--platform",
    type=click.Choice(PLATFORM_SERIES_TESTS.keys()),
    default=PLATFORM_SERIES_TESTS.keys(),
    multiple=True,
    help="Platform to run the tests on (requires credentials file for the clouds)",
)
@click.option(
    "-s",
    "--series",
    type=click.Choice(SERIES_TO_VERSION.keys()),
    default=SERIES_TO_VERSION.keys(),
    multiple=True,
    help="Series to run the tests on",
)
@click.option(
    "--token",
    "-t",
    type=click.Choice(TOKEN_TO_ENVVAR.keys()),
    default=TOKEN_TO_ENVVAR.keys(),
    multiple=True,
    help="Tokens to use for the tests (require tokens in the credentials file)",
)
@click.option(
    "--install-from",
    type=click.Choice(
        (
            "archive",
            "local",
            "daily",
            "staging",
            "stable",
            "proposed",
            "custom",
        )
    ),
    default="local",
    help="Choose the installation source for the uaclient deb",
)
@click.option(
    "--check-version",
    type=str,
    help="Check for a specific version in the tests",
)
@click.option(
    "--credentials-path",
    "-c",
    type=click.Path(dir_okay=False),
    default="tools/ua-test-credentials.yaml",
    help="Path to the file containing the credentials to run the test",
)
@click.option(
    "-w",
    "--wip",
    type=bool,
    default=False,
    is_flag=True,
    help="Run only tests with the @wip decorator",
)
def run_tests(
    platform, series, install_from, check_version, token, credentials_path, wip
):
    commands = build_commands(
        platform,
        series,
        install_from,
        check_version,
        token,
        credentials_path,
        wip,
    )
    current_datetime = datetime.now().strftime(format="%b-%d-%H%M")
    output_dir = "test-results/{}".format(current_datetime)
    os.makedirs(output_dir, exist_ok=True)
    error = False
    processes = []
    for name, command, env in commands:
        print("Running {}".format(command))
        with open("{}/{}.txt".format(output_dir, name), "wb") as result_file:
            process = subprocess.Popen(
                command, env=env, stdout=result_file, stderr=stdout
            )
            processes.append((name, process))

    while processes:
        for name, process in processes:
            result = process.poll()
            if result is not None:
                if result == 0:
                    print("{} finished sucessfully".format(process.args))
                else:
                    print("Failing tests for {}".format(process.args))
                    result_filename = "{}.txt".format(name)
                    os.rename(
                        "{}/{}".format(output_dir, result_filename),
                        "{}/failed-{}".format(output_dir, result_filename),
                    )
                    error = True
                processes.remove((name, process))
        time.sleep(5)

    if install_from == "proposed" and not error:
        filename = "test-results-{}.tar.gz".format(current_datetime)
        with tarfile.open(filename, "w:gz") as results:
            results.add(output_dir, arcname="test-results/")


if __name__ == "__main__":
    run_tests()
