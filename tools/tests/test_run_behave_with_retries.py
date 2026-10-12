import importlib.util
import os
import subprocess
import sys

import pytest

REPO_ROOT = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..")
)
FAKE_BEHAVE_DIR = os.path.join(
    REPO_ROOT,
    "tools",
    "tests",
    "fake_behave",
)
SCRIPT_PATH = os.path.join(
    REPO_ROOT,
    "tools",
    "run-behave-with-retries.py",
)
MALFORMED_FEATURE = os.path.join(
    REPO_ROOT,
    "tools",
    "tests",
    "fake_behave_malformed",
    "malformed.feature",
)


def _load_rerunner():
    spec = importlib.util.spec_from_file_location(
        "run_behave_with_retries", SCRIPT_PATH
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


rerunner = _load_rerunner()

# The subprocess-based tests below drive a real `tox -e behave` run, so gate
# them behind RUN_TOOL_TESTS. The build_behave_command unit tests are pure and
# always run.
requires_tool_tests = pytest.mark.skipif(
    os.environ.get("RUN_TOOL_TESTS") != "1",
    reason="set RUN_TOOL_TESTS=1 to run rerunner tool tests",
)


def _run_helper(
    tmpdir,
    selector,
    behave_args=None,
    max_attempts=None,
    max_failing_examples=None,
    use_feature_target=False,
):
    env = os.environ.copy()
    state_dir = tmpdir.mkdir("state")
    rerun_file = str(tmpdir.join("behave.rerun"))
    env["UACLIENT_BEHAVE_RETRY_STATE_DIR"] = str(state_dir)

    if use_feature_target:
        initial_target = os.path.relpath(
            os.path.join(FAKE_BEHAVE_DIR, selector), REPO_ROOT
        )
    else:
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
    if max_failing_examples is not None:
        command.extend(["--max-failing-examples", str(max_failing_examples)])

    command.append("--")
    if not use_feature_target:
        command.append("--tags=@{}".format(selector))
    command.extend(behave_args or ["--no-summary"])

    process = subprocess.run(
        command,
        cwd=REPO_ROOT,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        universal_newlines=True,
    )
    return process, str(state_dir), rerun_file


@pytest.mark.rerun_tool
@requires_tool_tests
class TestRunBehaveWithRetries:
    def test_passes_without_rerun_when_behave_is_clean(self, tmpdir):
        process, _state_dir, rerun_file = _run_helper(tmpdir, "suite_pass")

        assert process.returncode == 0, process.stdout + process.stderr
        assert "Retrying Behave for " not in process.stdout
        assert not os.path.exists(rerun_file)

    def test_retries_a_flaky_feature_once(self, tmpdir):
        process, state_dir, _rerun_file = _run_helper(tmpdir, "suite_flaky")

        assert process.returncode == 0, process.stdout + process.stderr
        assert os.path.exists(os.path.join(state_dir, "single"))
        assert "attempt 1/4 (initial)" in process.stdout
        assert "Retrying Behave for " in process.stdout
        assert "Failing rerun targets:" in process.stdout
        assert "(attempt 2/4)" in process.stdout

    def test_retries_until_max_attempts_then_fails(self, tmpdir):
        process, _state_dir, _rerun_file = _run_helper(
            tmpdir, "suite_always_fail"
        )

        assert process.returncode == 1
        assert "(attempt 2/4)" in process.stdout
        assert "(attempt 3/4)" in process.stdout
        assert "(attempt 4/4)" in process.stdout
        assert "Behave still failing after 4 attempts" in process.stderr

    def test_does_not_retry_when_failures_hit_threshold(self, tmpdir):
        process, _state_dir, _rerun_file = _run_helper(
            tmpdir, "suite_threshold"
        )

        assert process.returncode == 1
        assert "Retrying Behave for " not in process.stdout
        assert "Behave reported 10 failing examples" in process.stderr

    def test_does_not_retry_when_failures_exceed_threshold(self, tmpdir):
        process, _state_dir, _rerun_file = _run_helper(
            tmpdir, "suite_above_threshold"
        )

        assert process.returncode == 1
        assert "Retrying Behave for " not in process.stdout
        assert "Behave reported 11 failing examples" in process.stderr

    def test_fails_fast_without_rerun_targets(self, tmpdir):
        process, _state_dir, _rerun_file = _run_helper(
            tmpdir,
            os.path.relpath(MALFORMED_FEATURE, FAKE_BEHAVE_DIR),
            use_feature_target=True,
        )

        assert process.returncode == 1
        assert "Retrying Behave for " not in process.stdout
        assert (
            "Behave failed without rerun targets; not retrying"
            in process.stderr
        )

    def test_retries_multiple_failing_examples_and_then_passes(self, tmpdir):
        process, state_dir, _rerun_file = _run_helper(
            tmpdir, "suite_multi_flaky"
        )

        assert process.returncode == 0, process.stdout + process.stderr
        for key in ("one", "two", "three"):
            assert os.path.exists(os.path.join(state_dir, key))
        assert "Retrying Behave for " in process.stdout
        assert "(attempt 2/4)" in process.stdout

    def test_passes_behave_args_through_to_reruns(self, tmpdir):
        process, state_dir, _rerun_file = _run_helper(
            tmpdir,
            "suite_tagged",
            behave_args=["--no-summary", "--tags=@selected"],
        )

        assert process.returncode == 0, process.stdout + process.stderr
        assert os.path.exists(os.path.join(state_dir, "tagged"))
        assert "Retrying Behave for " in process.stdout


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
    def test_rerun_formatter_is_first_and_owns_the_outfile(self):
        command = rerunner.build_behave_command(
            "features", ["-D", "x=1"], "/tmp/rf"
        )
        formats, outfiles = _formats_and_outfiles(command)

        assert formats[0] == "rerun"
        assert outfiles == ["/tmp/rf"]

    def test_default_console_format_is_pretty_on_stdout(self):
        command = rerunner.build_behave_command("features", [], "/tmp/rf")
        formats, outfiles = _formats_and_outfiles(command)

        # Only one outfile, so pretty (index 1) falls back to stdout.
        assert formats == ["rerun", "pretty"]
        assert outfiles == ["/tmp/rf"]

    def test_console_format_none_disables_console_formatter(self):
        command = rerunner.build_behave_command(
            "features", [], "/tmp/rf", "none"
        )
        formats, outfiles = _formats_and_outfiles(command)

        assert formats == ["rerun"]
        assert outfiles == ["/tmp/rf"]

    def test_custom_console_format_passes_through(self):
        command = rerunner.build_behave_command(
            "features", [], "/tmp/rf", "plain"
        )
        formats, _outfiles = _formats_and_outfiles(command)

        assert formats == ["rerun", "plain"]

    def test_extra_format_in_behave_args_does_not_take_outfile(self):
        command = rerunner.build_behave_command(
            "features", ["--format", "json"], "/tmp/rf"
        )
        formats, outfiles = _formats_and_outfiles(command)

        # rerun stays first so it keeps the only outfile; extras hit stdout.
        assert formats[0] == "rerun"
        assert outfiles == ["/tmp/rf"]
        assert "json" in formats

    def test_console_format_defaults_to_pretty_in_parse_args(self):
        args = rerunner.parse_args(["--", "-D", "x=1"])

        assert args.console_format == "pretty"

    def test_max_attempts_defaults_to_four_in_parse_args(self):
        args = rerunner.parse_args(["--", "-D", "x=1"])

        assert args.max_attempts == 4
