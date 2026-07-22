from behave import when

from features.steps.packages import when_i_apt_install
from features.steps.shell import when_i_run_command, when_i_run_shell_command

LEGACY_OSCAP_SOURCE_BUILDS = {"xenial", "bionic", "focal", "jammy"}

OSCAP_137_BUILD_DEPS = " ".join(
    [
        "cmake",
        "libdbus-1-dev",
        "libdbus-glib-1-dev",
        "libcurl4-openssl-dev",
        "libgcrypt20-dev",
        "libselinux1-dev",
        "libxslt1-dev",
        "libgconf2-dev",
        "libacl1-dev",
        "libblkid-dev",
        "libcap-dev",
        "libxml2-dev",
        "libldap2-dev",
        "libpcre3-dev",
        "swig",
        "libxml-parser-perl",
        "libxml-xpath-perl",
        "libperl-dev",
        "libbz2-dev",
        "g++",
        "libapt-pkg-dev",
        "libyaml-dev",
        "libxmlsec1-dev",
        "libxmlsec1-openssl",
    ]
)


@when("I install the oscap tool")
def when_i_install_oscap_tool(context):
    """
    Install the OpenSCAP scanner tool.

    On older releases, this is built from source to avoid problems that were fixed in
    v1.3.7. This version is not available in `apt` until Noble.

    On Noble+, install directly using `apt`.

    See https://github.com/OpenSCAP/openscap.
    """

    release = getattr(context, "scenario_release", None)

    if release in LEGACY_OSCAP_SOURCE_BUILDS:
        _install_oscap_from_source(context)
    else:
        # Newer releases should use distro-packaged OpenSCAP when available.
        when_i_apt_install(context, "openscap-scanner")


def _install_oscap_from_source(context):
    when_i_apt_install(context, OSCAP_137_BUILD_DEPS)
    when_i_run_command(
        context,
        "wget https://github.com/OpenSCAP/openscap/releases/download/1.3.7/openscap-1.3.7.tar.gz",
        "as non-root",
    )
    when_i_run_command(
        context,
        "tar xzf openscap-1.3.7.tar.gz",
        "as non-root",
    )
    when_i_run_shell_command(
        context,
        "mkdir -p openscap-1.3.7/build",
        "as non-root",
    )
    when_i_run_shell_command(
        context,
        "cd openscap-1.3.7/build/ && cmake ..",
        "with sudo",
    )
    when_i_run_shell_command(
        context,
        "cd openscap-1.3.7/build/ && make",
        "with sudo",
    )
    when_i_run_shell_command(
        context,
        "cd openscap-1.3.7/build/ && make install",
        "with sudo",
    )
    when_i_run_command(context, "ldconfig", "with sudo")
