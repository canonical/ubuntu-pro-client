import json
import logging

import click

from features.util import build_debs, repo_state_hash


@click.command()
@click.argument("series")
@click.option(
    "-c",
    "--chroot",
    type=str,
    help="Use the supplied chroot when calling sbuild",
)
def main(series=None, chroot=None):
    logging.basicConfig()
    logging.getLogger().setLevel(logging.INFO)
    print(
        json.dumps(
            {
                "state_hash": repo_state_hash(),
                "debs": build_debs(series, chroot=chroot),
            }
        )
    )


if __name__ == "__main__":
    main()
