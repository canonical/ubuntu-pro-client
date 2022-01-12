import re
from collections import defaultdict

import click
import pycloudlib
import yaml

SUPPORTED_SERIES = ["xenial", "bionic", "focal", "jammy"]

FOOTER_MSG = """
Please submit a PR to update these default GCP images

git commit -am 'update: GCP Ubuntu PRO images'
git push upstream your-branch

Create a new pull request @ https://github.com/canonical/ubuntu-advantage-client/pulls
"""  # noqa


@click.command()
@click.option(
    "-cp", "--credentials-path", type=str, help="Credentials path for GCE"
)
@click.option("-p", "--project", type=str, help="project name used on GCE")
def main(credentials_path=None, project=None):
    series_bucket = defaultdict(list)
    latest_images = dict()

    api = pycloudlib.GCE(
        tag="uaclient-gcp-images",
        credentials_path=credentials_path,
        project=project,
        zone="a",
        region="us-west2",
    )

    pro_images_resp = (
        api.compute.images().list(project="ubuntu-os-pro-cloud").execute()
    )

    for image in pro_images_resp.get("items", []):
        if not image["name"].startswith("ubuntu-pro"):
            continue

        m = re.match(r"^ubuntu-pro-\d+-(?P<release>\w+)-v\d+", image["name"])
        if not m:
            print("Skipping unexpected image name: ", image["name"])
            continue
        elif m.group("release") in SUPPORTED_SERIES:
            release = m.group("release")
            series_bucket[release].append(image["name"])

    for series, images in series_bucket.items():
        latest_images[series] = "{}{}".format(
            "projects/ubuntu-os-pro-cloud/global/images/", sorted(images)[-1]
        )

    update_images = False
    with open("features/gcp-ids.yaml", "r+") as stream:
        curr_images = yaml.safe_load(stream)

        if curr_images != latest_images:
            stream.seek(0)
            stream.write(yaml.dump(latest_images, default_flow_style=False))
            print(FOOTER_MSG)
        else:
            print("UA is already using the latest gcp images")


if __name__ == "__main__":
    main()
