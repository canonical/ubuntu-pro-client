import os
from datetime import datetime

from uaclient.apt import is_installed, run_apt_command, run_apt_install_command
from uaclient.exceptions import AnonymousUbuntuProError, UbuntuProError
from uaclient.messages import NamedMessage
from uaclient.system import write_file
from uaclient.util import prompt_for_confirmation, we_are_currently_root

SERIES_NOT_SUPPORTED = ["xenial", "bionic", "focal"]


def check_for_hwlib_package() -> bool:
    if is_installed("hwlib"):
        return True

    if not we_are_currently_root():
        print(
            "To get certification status, the 'hwlib' package "
            "needs to be installed."
        )
        print("Run this command as root, or install it by running:")
        print("    sudo apt install hwlib")
        return False

    if not prompt_for_confirmation(
        "To get certification status, the 'hwlib' package "
        "needs to be installed.\nDo you want to install it now? (Y/n)",
        default=True,
    ):
        return False

    print("Installing 'hwlib'")
    try:
        # In the future, the package will be in the archive, no need for a PPA
        run_apt_command(["apt-add-repository", "ppa:nhutsko/ppa", "-y"])
        run_apt_install_command(
            ["hwlib"],
            apt_options=[
                "--allow-downgrades",
                '-o Dpkg::Options::="--force-confdef"',
                '-o Dpkg::Options::="--force-confold"',
            ],
            override_env_vars={"DEBIAN_FRONTEND": "noninteractive"},
        )
    except UbuntuProError:
        # The actual implementation will have proper exceptions
        raise AnonymousUbuntuProError(
            named_msg=NamedMessage(
                "could-not-install-hwlib",
                "Error trying to install the 'hwlib' package.\n"
                "Try to install it by running:"
                "    sudo apt install hwlib",
            )
        )

    return True


def check_for_data_collection_consent() -> bool:
    # In the future, there will be a hwlib api to check for this instead of
    # just checking for the file.
    if os.path.exists("/var/lib/hwlib/consent"):
        return True

    if not we_are_currently_root():
        # In the future, there will be a URL here with the details
        # about data collection.
        print(
            "To check for certification status, data from your system needs to"
            " be sent to our servers. Details about the data can be checked in"
            " <URL>."
        )
        print(
            "To agree with sending hardware data, "
            "please run this command as root."
        )
        return False

    if not prompt_for_confirmation(
        "To check for certification status, data from your system needs to"
        " be sent to our servers. Details about the data can be checked in"
        " <URL>.\n"
        "Do you agree with sending hardware data for checking? (y/N)"
    ):
        print(
            "The client needs user consent to check "
            "for the certification status."
        )
        return False

    write_file("/var/lib/hwlib/consent", datetime.now().isoformat())
    return True


def get_certification_status() -> str:
    try:
        import hwlib  # type: ignore
    except ImportError:
        raise AnonymousUbuntuProError(
            named_msg=NamedMessage(
                "import-hwlib-without-installing",
                "Trying to import 'hwlib' but it is not installed."
                "Please install the package and try again.",
            )
        )

    # In the future, the empty string here will not be mandatory -
    # it will be a default, configurable in the
    # hwlib side. We should not hardcode anything here.
    response = hwlib.get_certification_status("")

    status = response.get("status", None)
    if status is None:
        raise AnonymousUbuntuProError(
            named_msg=NamedMessage(
                "no-status-from-hwlib",
                "The 'hwlib' client did not return a valid status "
                "for certification.\nThis error message can be more "
                "descriptive in the future on what to check for."
            )
        )

    if status == "Not Seen":
        # We intentionally give no additional details here.
        return "No"
    elif status == "Partially Certified":
        # For a partially certified system, we can give a list of which
        # hardware is actually certified.
        return "Partially"
    else:
        # In the future, besides saying yes, hwlib will give us a link
        # to the certification page which will cover everything.
        return "Yes"
