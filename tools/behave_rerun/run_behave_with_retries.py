#!/usr/bin/python3
"""Run behave, rerunning only the failed scenarios, to absorb flaky tests.

This runs ``tox -e behave``. When behave fails, it reruns only the scenarios
listed in behave's rerun file, up to ``--max-attempts`` runs in total. It does
not retry when behave fails without listing any scenario, or when
``--max-failing-scenarios`` or more scenarios fail, which points to a real
breakage rather than flaky tests.

Behave runs with the formatter and runner in ``behave_plugins.py``. They make
sure a failed feature that has no failing scenario is listed in the rerun
file, and that an aborted run is not retried, so a passing rerun cannot hide
anything that failed or never ran.

Example::

    python3 tools/behave_rerun/run_behave_with_retries.py \
        --rerun-file /tmp/behave.rerun \
        -- -D machine_types=lxd-container -D releases=resolute
"""

import argparse
import functools
import os
import subprocess
import sys
import tempfile

RERUN_FORMATTER = "behave_plugins:FeatureRerunFormatter"
RUNNER = "behave_plugins:AbortAwareRunner"

# Flush so these lines stay in order with behave's output in CI logs.
log = functools.partial(print, flush=True)


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--rerun-file",
        default=os.path.join(tempfile.gettempdir(), "behave.rerun"),
        help="path to behave's rerun file (default: %(default)s)",
    )
    parser.add_argument(
        "--max-attempts",
        type=int,
        default=4,
        help=(
            "maximum number of behave runs, counting the first "
            "(default: %(default)s)"
        ),
    )
    parser.add_argument(
        "--max-failing-scenarios",
        type=int,
        default=10,
        help=(
            "do not retry when this many or more scenarios fail "
            "(default: %(default)s)"
        ),
    )
    parser.add_argument(
        "--initial-target",
        default="features",
        help="feature path for the first behave run (default: %(default)s)",
    )
    parser.add_argument(
        "behave_args",
        nargs=argparse.REMAINDER,
        help="arguments passed to behave on every run, after `--`",
    )
    args = parser.parse_args(argv)
    if args.behave_args[:1] == ["--"]:
        args.behave_args = args.behave_args[1:]
    return args


def build_behave_command(target, behave_args, rerun_file):
    # Behave pairs --format and --outfile by position: the rerun formatter
    # comes first so it owns the outfile, and pretty, which has no outfile,
    # writes to stdout. Without pretty, behave would print no console output,
    # as it drops it when --format is given without a formatter for stdout.
    return (
        ["tox", "-e", "behave", "--", target]
        + ["--runner", RUNNER]
        + ["--format", RERUN_FORMATTER, "--outfile", rerun_file]
        + list(behave_args)
        + ["--format", "pretty"]
    )


def read_rerun_entries(rerun_file):
    """Return the rerun file's entries as absolute paths.

    Behave writes them relative to the working directory, but resolves the
    entries of an ``@file`` target relative to that file's directory.
    """
    if not os.path.exists(rerun_file):
        return []
    with open(rerun_file) as stream:
        entries = [line.strip() for line in stream]
    return [
        os.path.abspath(entry)
        for entry in entries
        if entry and not entry.startswith("#")
    ]


def run_with_retries(args, caller=subprocess.call):
    os.makedirs(
        os.path.dirname(os.path.abspath(args.rerun_file)), exist_ok=True
    )
    if os.path.exists(args.rerun_file):
        os.unlink(args.rerun_file)

    target = args.initial_target
    for attempt in range(1, args.max_attempts + 1):
        command = build_behave_command(
            target, args.behave_args, args.rerun_file
        )
        log(
            "Behave attempt {}/{}: {}".format(
                attempt, args.max_attempts, " ".join(command)
            )
        )
        if caller(command) == 0:
            return 0

        entries = read_rerun_entries(args.rerun_file)
        if not entries:
            log(
                "Behave failed without rerun targets; not retrying",
                file=sys.stderr,
            )
            return 1
        log("Failing scenarios:")
        for entry in entries:
            log("  {}".format(entry))
        if len(entries) >= args.max_failing_scenarios:
            log(
                "Behave reported {} failing scenarios; not retrying".format(
                    len(entries)
                ),
                file=sys.stderr,
            )
            return 1

        with open(args.rerun_file, "w") as stream:
            stream.write("".join(entry + "\n" for entry in entries))
        target = "@{}".format(args.rerun_file)

    log(
        "Behave still failing after {} attempts".format(args.max_attempts),
        file=sys.stderr,
    )
    return 1


def main(argv=None):
    return run_with_retries(parse_args(argv))


if __name__ == "__main__":
    sys.exit(main())
