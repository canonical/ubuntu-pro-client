#!/usr/bin/python3
"""Run behave with bounded reruns for a small number of failures.

This helper runs ``tox -e behave`` once against an initial target and, on
failure, uses Behave's ``rerun`` formatter output to retry only the failed
scenario/example locations. Retries stop when the suite passes, when the rerun
file is empty, when the number of failing locations reaches the configured
limit, or when the rerun limit is exhausted.

Examples::

    python3 tools/run-behave-with-retries.py \
        --runner-group lxd \
        --rerun-file /tmp/behave.rerun \
        -- -D machine_types=lxd-container -D releases=resolute

    python3 tools/run-behave-with-retries.py \
        --initial-target features/cli/attach.feature \
        -- --tags=-slow
"""

from __future__ import print_function

import argparse
import os
import shlex
import subprocess
import sys


def parse_args(argv=None):
    parser = argparse.ArgumentParser(
        description="Run behave with bounded reruns for a small number of failures."
    )
    parser.add_argument(
        "--rerun-file",
        default=os.environ.get(
            "RERUN_FILE",
            os.path.join(os.environ.get("TMPDIR", "/tmp"), "behave.rerun"),
        ),
        help="path to Behave rerun file",
    )
    parser.add_argument(
        "--max-reruns",
        type=int,
        default=int(os.environ.get("MAX_RERUNS", 3)),
        help="maximum number of reruns after the initial failure",
    )
    parser.add_argument(
        "--max-failing-examples",
        type=int,
        default=int(os.environ.get("MAX_FAILING_EXAMPLES", 10)),
        help="do not retry when failing locations reach this count",
    )
    parser.add_argument(
        "--initial-target",
        default=os.environ.get("INITIAL_TARGET", "features"),
        help="feature path or @rerun file target for the first behave run",
    )
    parser.add_argument(
        "--runner-group",
        default=os.environ.get("BEHAVE_RUNNER_GROUP", ""),
        help="optional Unix group name to use via sg -c",
    )
    parser.add_argument(
        "behave_args",
        nargs=argparse.REMAINDER,
        help="arguments passed to `tox -e behave --`",
    )

    args = parser.parse_args(argv)
    if args.behave_args[:1] == ["--"]:
        args.behave_args = args.behave_args[1:]
    return args


def build_behave_command(target, behave_args, rerun_file):
    return (
        [
            "tox",
            "-e",
            "behave",
            "--",
            target,
        ]
        + list(behave_args)
        + [
            "--format",
            "rerun",
            "--outfile",
            rerun_file,
        ]
    )


def run_command(command, runner_group=None, caller=None):
    caller = caller or subprocess.call
    if runner_group:
        quoted = " ".join(shlex.quote(arg) for arg in command)
        return caller(["sg", runner_group, "-c", quoted])
    return caller(command)


def load_rerun_entries(rerun_file, cwd):
    """Behave emits relative paths for re-runs. If the file isn't emitted to
    repo root, Behave fails to discover steps. Re-write failures as absolute
    paths to fix this.
    """

    entries = []
    with open(rerun_file) as stream:
        for line in stream:
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue

            if ":" in stripped:
                feature_path, line_number = stripped.rsplit(":", 1)
                feature_path = os.path.abspath(os.path.join(cwd, feature_path))
                entries.append("{}:{}".format(feature_path, line_number))
            else:
                entries.append(os.path.abspath(os.path.join(cwd, stripped)))
    return entries


def count_failing_examples(rerun_file):
    return len(load_rerun_entries(rerun_file, os.getcwd()))


def normalize_rerun_file(rerun_file, cwd):
    entries = load_rerun_entries(rerun_file, cwd)
    with open(rerun_file, "w") as stream:
        for entry in entries:
            stream.write("{}\n".format(entry))


def run_with_retries(args, caller=None, printer=None):
    printer = printer or print
    rerun_count = 0
    cwd = os.getcwd()

    if os.path.exists(args.rerun_file):
        os.unlink(args.rerun_file)

    while True:
        if rerun_count == 0:
            behave_target = args.initial_target
        else:
            behave_target = "@{}".format(args.rerun_file)

        command = build_behave_command(
            behave_target, args.behave_args, args.rerun_file
        )
        if run_command(command, args.runner_group, caller=caller) == 0:
            return 0

        if (
            not os.path.exists(args.rerun_file)
            or os.path.getsize(args.rerun_file) == 0
        ):
            printer(
                "Behave failed without rerun targets; not retrying",
                file=sys.stderr,
            )
            return 1

        normalize_rerun_file(args.rerun_file, cwd)
        failing_examples = count_failing_examples(args.rerun_file)
        if failing_examples >= args.max_failing_examples:
            printer(
                "Behave reported {} failing examples; not retrying".format(
                    failing_examples
                ),
                file=sys.stderr,
            )
            return 1

        if rerun_count >= args.max_reruns:
            printer(
                "Behave still failing after {} reruns".format(rerun_count),
                file=sys.stderr,
            )
            return 1

        rerun_count += 1
        printer(
            "Retrying Behave for {} failing examples (rerun {}/{})".format(
                failing_examples, rerun_count, args.max_reruns
            )
        )


def main(argv=None):
    return run_with_retries(parse_args(argv))


if __name__ == "__main__":
    sys.exit(main())
