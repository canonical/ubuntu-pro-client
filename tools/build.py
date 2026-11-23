import json
import logging
import os
import shutil

import click

from features.util import build_debs, repo_state_hash


@click.command()
@click.argument("series")
@click.option(
    "-a",
    "--arch",
    type=str,
    help="Architecture to use in the build",
)
@click.option(
    "-q",
    "--quiet",
    is_flag=True,
    default=False,
    help="Don't show sbuild output",
)
@click.option(
    "-o",
    "--output-dir",
    type=click.Path(file_okay=False),
    help="Also copy the built debs into this directory",
)
def main(series=None, arch=None, quiet=False, output_dir=None):
    logging.basicConfig()
    logging.getLogger().setLevel(logging.INFO)
    debs = build_debs(
        series,
        sbuild_output_to_terminal=not quiet,
        architecture=arch,
    ).__dict__
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)
        for name, path in debs.items():
            if path and os.path.exists(path):
                debs[name] = shutil.copy(path, output_dir)
    print(json.dumps({"state_hash": repo_state_hash(), "debs": debs}))


if __name__ == "__main__":
    main()
