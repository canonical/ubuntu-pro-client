import mock
import pytest

from uaclient.cli import main

HELP_OUTPUT = """\
usage: pro system reboot-required [flags]

Report the current reboot-required status for the machine.

This command will output one of the three following states
for the machine regarding reboot:

* no: The machine doesn't require a reboot
* yes: The machine requires a reboot
* yes-kernel-livepatches-applied: There are only kernel related
  packages that require a reboot, but Livepatch has already provided
  patches for the current running kernel. The machine still needs a
  reboot, but you can assess if the reboot can be performed in the
  nearest maintenance window.
"""


class TestActionRebootRequired:
    @mock.patch("uaclient.log.setup_cli_logging")
    def test_enable_help(self, _m_setup_logging, capsys, FakeConfig):
        with pytest.raises(SystemExit):
            with mock.patch(
                "sys.argv",
                ["/usr/bin/ua", "system", "reboot-required", "--help"],
            ):
                with mock.patch(
                    "uaclient.config.UAConfig",
                    return_value=FakeConfig(),
                ):
                    main()
        out, _err = capsys.readouterr()
        assert HELP_OUTPUT in out
