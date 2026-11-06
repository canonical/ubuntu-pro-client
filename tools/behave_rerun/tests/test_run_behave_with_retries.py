import argparse
import importlib.util
import os
import subprocess
import sys

TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
TOOL_DIR = os.path.dirname(TESTS_DIR)
REPO_ROOT = os.path.dirname(os.path.dirname(TOOL_DIR))
FAKE_BEHAVE_DIR = os.path.join(TESTS_DIR, "fake_behave")
SCRIPT_PATH = os.path.join(TOOL_DIR, "run_behave_with_retries.py")
# --no-junit keeps behave from writing reports into the repository.
DEFAULT_BEHAVE_ARGS = ["--no-summary", "--no-junit"]


def _load_rerunner():
    spec = importlib.util.spec_from_file_location(
        "run_behave_with_retries", SCRIPT_PATH
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


rerunner = _load_rerunner()


def _run_helper(
    tmpdir,
    selector,
    behave_args=None,
    max_attempts=None,
    max_failing_scenarios=None,
    initial_target=None,
):
    env = os.environ.copy()
    state_dir = tmpdir.mkdir("state")
    rerun_file = str(tmpdir.join("behave.rerun"))
    env["UACLIENT_BEHAVE_RETRY_STATE_DIR"] = str(state_dir)

    if initial_target is None:
        initial_target = os.path.relpath(FAKE_BEHAVE_DIR, REPO_ROOT)

    command = [
        sys.executable,
        SCRIPT_PATH,
        "--initial-target",
        initial_target,
        "--rerun-file",
        rerun_file,
    ]
    if max_attempts is not None:
        command.extend(["--max-attempts", str(max_attempts)])
    if max_failing_scenarios is not None:
        command.extend(["--max-failing-scenarios", str(max_failing_scenarios)])

    command.append("--")
    if selector:
        command.append("--tags=@{}".format(selector))
    command.extend(behave_args or DEFAULT_BEHAVE_ARGS)

    process = subprocess.run(
        command,
        cwd=REPO_ROOT,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        universal_newlines=True,
    )
    return process, str(state_dir), rerun_file


class TestE2E:
    """Run the script end to end, as CI does: through `tox -e behave`, with
    real behave and real feature files."""

    def test_passes_without_rerun_when_behave_is_clean(self, tmpdir):
        process, _state_dir, rerun_file = _run_helper(tmpdir, "suite_pass")

        assert process.returncode == 0, process.stdout + process.stderr
        assert "Behave attempt 2/" not in process.stdout
        assert not os.path.exists(rerun_file)

    def test_retries_a_flaky_feature_once(self, tmpdir):
        process, state_dir, _rerun_file = _run_helper(tmpdir, "suite_flaky")

        assert process.returncode == 0, process.stdout + process.stderr
        assert os.path.exists(os.path.join(state_dir, "single"))
        assert "Behave attempt 1/4" in process.stdout
        assert "Failing scenarios:" in process.stdout
        assert "Behave attempt 2/4" in process.stdout

    def test_retries_until_max_attempts_then_fails(self, tmpdir):
        process, _state_dir, _rerun_file = _run_helper(
            tmpdir, "suite_always_fail"
        )

        assert process.returncode == 1
        assert "Behave attempt 4/4" in process.stdout
        assert "Behave still failing after 4 attempts" in process.stderr

    def test_does_not_retry_when_failures_hit_threshold(self, tmpdir):
        process, _state_dir, _rerun_file = _run_helper(
            tmpdir, "suite_threshold"
        )

        assert process.returncode == 1
        assert "Behave attempt 2/" not in process.stdout
        assert "Behave reported 10 failing scenarios" in process.stderr

    def test_does_not_retry_when_failures_exceed_threshold(self, tmpdir):
        process, _state_dir, _rerun_file = _run_helper(
            tmpdir, "suite_above_threshold"
        )

        assert process.returncode == 1
        assert "Behave attempt 2/" not in process.stdout
        assert "Behave reported 11 failing scenarios" in process.stderr

    def test_fails_fast_without_rerun_targets(self, tmpdir):
        # Kept out of the repository: it cannot be parsed, which would also
        # break the reformat-gherkin pre-commit hook.
        malformed = tmpdir.join("malformed.feature")
        malformed.write(
            "Feature malformed suite\n\n"
            "  Scenario broken syntax\n"
            "    Given this file does not parse correctly\n"
        )
        process, _state_dir, _rerun_file = _run_helper(
            tmpdir, None, initial_target=str(malformed)
        )

        assert process.returncode == 1
        assert "Behave attempt 2/" not in process.stdout
        assert (
            "Behave failed without rerun targets; not retrying"
            in process.stderr
        )

    def test_retries_multiple_failing_outline_rows_and_then_passes(
        self, tmpdir
    ):
        process, state_dir, _rerun_file = _run_helper(
            tmpdir, "suite_multi_flaky"
        )

        assert process.returncode == 0, process.stdout + process.stderr
        for key in ("one", "two", "three"):
            assert os.path.exists(os.path.join(state_dir, key))
        assert "Behave attempt 2/4" in process.stdout

    def test_reruns_a_feature_whose_feature_hook_failed(self, tmpdir):
        # The neighbouring flaky scenario alone would pass on a rerun. The
        # feature whose before_feature hook failed never ran its failing
        # scenario, so the whole feature must be rerun, and that scenario
        # must then run and keep the result failing.
        process, _state_dir, _rerun_file = _run_helper(
            tmpdir, "suite_feature_hook", max_attempts=2
        )

        assert process.returncode == 1
        assert "feature_hook_error.feature:2" in process.stdout
        assert "feature_hook_error.feature:4" in process.stdout
        assert "Behave still failing after 2 attempts" in process.stderr

    def test_does_not_retry_after_an_aborted_run(self, tmpdir):
        # The abort stops behave before the last feature, which always
        # fails, runs. Rerunning only the flaky scenario would pass.
        process, _state_dir, _rerun_file = _run_helper(tmpdir, "suite_abort")

        assert process.returncode == 1, process.stdout + process.stderr
        assert "ABORTED" in process.stdout + process.stderr
        assert "Behave attempt 2/" not in process.stdout
        assert (
            "Behave failed without rerun targets; not retrying"
            in process.stderr
        )

    def test_retries_with_a_tag_filter(self, tmpdir):
        process, state_dir, _rerun_file = _run_helper(
            tmpdir,
            "suite_tagged",
            behave_args=DEFAULT_BEHAVE_ARGS + ["--tags=@selected"],
        )

        assert process.returncode == 0, process.stdout + process.stderr
        assert os.path.exists(os.path.join(state_dir, "tagged"))
        assert "Behave attempt 2/4" in process.stdout


def _formats_and_outfiles(command):
    """Split a behave command into ordered --format and --outfile values.

    Behave pairs the two lists positionally, so preserving order lets tests
    assert which formatter receives the rerun outfile.
    """
    formats = []
    outfiles = []
    index = 0
    while index < len(command):
        if command[index] == "--format":
            formats.append(command[index + 1])
            index += 2
        elif command[index] == "--outfile":
            outfiles.append(command[index + 1])
            index += 2
        else:
            index += 1
    return formats, outfiles


class TestBuildBehaveCommand:
    def test_runs_tox_behave_with_the_plugins(self):
        command = rerunner.build_behave_command("features", [], "/tmp/rf")

        assert command[:5] == ["tox", "-e", "behave", "--", "features"]
        assert command[command.index("--runner") + 1] == rerunner.RUNNER

    def test_rerun_formatter_owns_the_outfile_and_pretty_goes_to_stdout(
        self,
    ):
        command = rerunner.build_behave_command(
            "features", ["--format", "json"], "/tmp/rf"
        )
        formats, outfiles = _formats_and_outfiles(command)

        # Behave pairs formats and outfiles by position; any format after
        # the only outfile writes to stdout.
        assert formats == [rerunner.RERUN_FORMATTER, "json", "pretty"]
        assert outfiles == ["/tmp/rf"]


class FakeBehave:
    """Stand-in for running behave: each call takes the next planned
    (exit code, rerun lines) pair and writes those lines to the rerun file,
    as behave's rerun formatter would. None means no rerun file is written.
    """

    def __init__(self, attempts):
        self.attempts = list(attempts)
        self.commands = []

    def __call__(self, command):
        self.commands.append(command)
        returncode, rerun_lines = self.attempts.pop(0)
        _formats, outfiles = _formats_and_outfiles(command)
        if rerun_lines is None:
            if os.path.exists(outfiles[0]):
                os.unlink(outfiles[0])
        else:
            with open(outfiles[0], "w") as stream:
                stream.write("".join(line + "\n" for line in rerun_lines))
        return returncode


def _failing(count):
    return ["features/x.feature:{}".format(line) for line in range(count)]


class TestRunWithRetries:
    def _run(self, tmpdir, attempts, **arg_overrides):
        args = argparse.Namespace(
            rerun_file=str(tmpdir.join("behave.rerun")),
            max_attempts=4,
            max_failing_scenarios=10,
            initial_target="features",
            behave_args=["-D", "releases=noble"],
        )
        for name, value in arg_overrides.items():
            setattr(args, name, value)
        fake = FakeBehave(attempts)
        result = rerunner.run_with_retries(args, caller=fake)
        return result, fake.commands

    def test_reruns_only_the_rerun_file_after_a_failure(self, tmpdir):
        result, commands = self._run(tmpdir, [(1, _failing(1)), (0, None)])

        rerun_target = "@{}".format(tmpdir.join("behave.rerun"))
        assert result == 0
        assert "features" in commands[0]
        assert rerun_target not in commands[0]
        assert rerun_target in commands[1]

    def test_retries_just_below_the_failure_threshold(self, tmpdir):
        # The real tests cover 10 and 11 failures; this is the other side.
        result, commands = self._run(tmpdir, [(1, _failing(9)), (0, None)])

        assert result == 0
        assert len(commands) == 2

    def test_passes_behave_args_to_every_attempt(self, tmpdir):
        _result, commands = self._run(
            tmpdir, [(1, _failing(1)), (1, _failing(1)), (0, None)]
        )

        assert len(commands) == 3
        for command in commands:
            index = command.index("-D")
            assert command[index : index + 2] == ["-D", "releases=noble"]
