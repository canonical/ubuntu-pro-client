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
    "hirsute": "21.04",
}

TOKEN_TO_ENVVAR = {
    "prod": "UACLIENT_BEHAVE_CONTRACT_TOKEN",
    "staging": "UACLIENT_BEHAVE_CONTRACT_TOKEN_STAGING",
    "expired": "UACLIENT_BEHAVE_CONTRACT_TOKEN_STAGING_EXPIRED",
}

PLATFORM_SERIES_TESTS = {
    "azuregeneric": ["xenial", "bionic", "focal"],
    "azurepro": ["xenial", "bionic", "focal"],
    "awsgeneric": ["xenial", "bionic", "focal"],
    "awspro": ["xenial", "bionic", "focal"],
    "gcpgeneric": ["xenial", "bionic", "focal", "hirsute"],
    "gcppro": ["xenial", "bionic", "focal"],
    "vm": ["xenial", "bionic", "focal"],
    "lxd": ["xenial", "bionic", "focal", "hirsute"],
    "upgrade": ["xenial", "bionic", "focal", "hirsute"],
}


def is_compatible(platform, series):
    return series in PLATFORM_SERIES_TESTS[platform]


def build_commands(
    platform, series, proposed, check_version, token, credentials_path, wip
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

                # Add check_version variable
                if check_version:
                    env["UACLIENT_BEHAVE_CHECK_VERSION"] = "{}~{}.1".format(
                        check_version, series_version
                    )

                # If not told to run from proposed, run from local changes
                if proposed:
                    env["UACLIENT_BEHAVE_ENABLE_PROPOSED"] = "1"
                else:
                    env["UACLIENT_BEHAVE_BUILD_PR"] = "1"

                # Inject tokens from credentials
                for t in token:
                    envvar = TOKEN_TO_ENVVAR[t]
                    env[envvar] = credentials["token"].get(envvar)

                # Inject cloud-specific variables from credentials
                for cloud in ("azure", "aws", "gcp"):
                    if cloud in p:
                        for envvar in credentials[cloud]:
                            env[envvar] = credentials[cloud].get(envvar)

                # Until we don't get sbuild to run just once per run,
                env["UACLIENT_BEHAVE_SNAPSHOT_STRATEGY"] = "1"

                # Tox command itself
                command = "tox -e behave-{}-{}".format(
                    p, series_version
                ).split()

                # Wip
                if wip:
                    command.extend(["--", "--tags=wip", "--stop"])

                commands.append((command, env))

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
    "--proposed",
    type=bool,
    default=False,
    is_flag=True,
    help="Run tests based on existing packages in the Proposed pocket",
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
    platform, series, proposed, check_version, token, credentials_path, wip
):
    commands = build_commands(
        platform, series, proposed, check_version, token, credentials_path, wip
    )
    current_datetime = datetime.now().strftime(format="%b-%d-%H%M")
    output_dir = "test-results/{}".format(current_datetime)
    os.makedirs(output_dir, exist_ok=True)
    error = False
    processes = []
    for command, env in commands:
        print("Running {}".format(command))
        with open(
            "{}/{}.txt".format(output_dir, command[2]), "wb"
        ) as result_file:
            process = subprocess.Popen(
                command, env=env, stdout=result_file, stderr=stdout
            )
            processes.append(process)

    while processes:
        for process in processes:
            result = process.poll()
            if result is not None:
                if result == 0:
                    print("{} finished sucessfully".format(process.args))
                else:
                    print("Failing tests for {}".format(process.args))
                    result_filename = "{}.txt".format(process.args[2])
                    os.rename(
                        "{}/{}".format(output_dir, result_filename),
                        "{}/failed-{}".format(output_dir, result_filename),
                    )
                    error = True
                processes.remove(process)
        time.sleep(5)

    if proposed and not error:
        filename = "test-results-{}.tar.gz".format(current_datetime)
        with tarfile.open(filename, "w:gz") as results:
            results.add(output_dir, arcname="test-results/")


if __name__ == "__main__":
    run_tests()
