# How to maintain the target list

`features/targets.yaml` lists which Ubuntu releases each machine type is
offered on. A target is one release on one machine type, such as noble on
`lxd-vm`. A target that the file does not list cannot be used in a feature
test.

Update the file when:

* a new Ubuntu series is released,
* an Ubuntu release ages out of support,
* a machine type gains or loses support for a release, or
* a new machine type is introduced.

## File format

Each key is a machine type name from `MachineType` in
`features/machine_types.py`. Each value is the complete list of Ubuntu release
codenames the machine type is offered on:

```yaml
aws.pro-fips:
  - bionic
  - focal
  - jammy
```

A release that is not listed for a machine type is not applicable to it.

## Add a new release

1. Find which machine types offer the release (see
   [Check what a publisher offers](#check-what-a-publisher-offers)).
2. Add the codename to each of those machine types, after the previous
   release.
3. Leave the release out of any machine type that does not offer it. For
   example, no cloud publishes Pro images for interim releases, so an interim
   release belongs under the `*.generic` and LXD types only.
4. Run the check described in [Validate the change](#validate-the-change).

## Add a machine type

1. Add the machine type to `MachineType` in `features/machine_types.py`.
2. Add a key with the same name to `features/targets.yaml`, listing every
   release it is offered on.
3. Add the new name to the expected set in `TestRepositoryData` in
   `features/tools/tests/test_targets.py`.

## Remove a release

An LTS release should be removed when its ESM period ends and it enters Legacy
support. An interim release should be removed at its end of its support period.
See [Ubuntu release and branch policy](../explanation/release_and_branch_policy.md).

1. Run `ubuntu-distro-info --supported-esm` and
   `ubuntu-distro-info --supported`. A release that appears in neither list
   should be removed.
2. Delete the release from every machine type in `features/targets.yaml`.
3. Update any expectation in `TestRepositoryData` that refers to the release.
4. Run the check described in [Validate the change](#validate-the-change).

## Check what a publisher offers

For each cloud, list the images the publisher offers, then work out which
releases each machine type (`generic`, `pro`, `pro-fips`) has an image for.

### AWS

Canonical publishes generic and Pro images as SSM parameters. This lists them
(`aws.generic`, then `aws.pro`):

```bash
for product in server pro-server; do
  aws ssm get-parameters-by-path --region us-east-1 --recursive \
    --path /aws/service/canonical/ubuntu/$product \
    --query "Parameters[?contains(Name, '/current/amd64/hvm')].Name" \
    --output text | tr '\t' '\n' | sort
done
```

The release is the version (`24.04`) or codename (`noble`) in each path, for
example `.../server/24.04/stable/current/amd64/hvm/ebs-gp3/ami-id`.

FIPS images are Marketplace AMIs, so they are not in that SSM hierarchy. List
them (`aws.pro-fips`) with:

```bash
aws ec2 describe-images --region us-east-1 --owners aws-marketplace \
  --include-deprecated \
  --filters "Name=name,Values=ubuntu-pro-fips*" \
  --query "Images[].Name" --output text | tr '\t' '\n' | sort
```

Names start with `ubuntu-pro-fips/` or `ubuntu-pro-fips-updates-server/` and
contain the release as a codename and version, such as
`ubuntu-jammy-22.04-amd64-pro-fips-updates-server-...`. Both the `fips` and
`fips-updates` services count as FIPS images.

[Find Ubuntu images on AWS](https://ubuntu.com/aws/docs/aws-how-to/instances/find-ubuntu-images/)
describes the same parameters.

### Azure

Every image belongs to an offer, and each offer has SKUs. This prints every
Canonical Ubuntu `offer:sku` pair:

```bash
for offer in $(az vm image list-offers --location eastus --publisher Canonical \
    --query "[?contains(name, 'ubuntu')].name" -o tsv); do
  az vm image list-skus --location eastus --publisher Canonical \
    --offer "$offer" --query "[].name" -o tsv | sed "s/^/$offer:/"
done
```

The naming is not uniform across releases, so read the pairs rather than
relying on a pattern. The release is in the offer name (`ubuntu-24_04-lts`,
`0001-com-ubuntu-server-jammy`) or the SKU name (`pro-20_04-lts`). Then:

* `azure.generic`: server offers and SKUs without `pro` in the name.
* `azure.pro`: names containing `pro` but not `fips`, such as
  `0001-com-ubuntu-pro-focal`, `ubuntu-pro` or `pro-server`.
* `azure.pro-fips`: names containing `fips`.

[Find Ubuntu images on Azure](https://ubuntu.com/azure/docs/azure-how-to/instances/find-ubuntu-images/)
has a table of the common images as well. It does not include the older images
that we still test, so the CLI command above is preferable.

### GCP

Generic images are in the `ubuntu-os-cloud` project, and Pro and FIPS images
are in `ubuntu-os-pro-cloud`. `--no-standard-images` limits the output to the
named project:

```bash
gcloud compute images list --project ubuntu-os-cloud \
  --no-standard-images --show-deprecated \
  --format="table(name,deprecated.state)"

gcloud compute images list --project ubuntu-os-pro-cloud \
  --no-standard-images --show-deprecated \
  --format="table(name,deprecated.state)"
```

Names are the product, version and series, followed by a build date. For
example, `ubuntu-2404-noble-amd64-v20261125` is generic and
`ubuntu-pro-2204-jammy-v20261125` is Pro. Then:

* `gcp.generic`: names starting with `ubuntu-` and a version, from
  `ubuntu-os-cloud`. Ignore `ubuntu-minimal-` and `ubuntu-accelerator-` images.
* `gcp.pro`: names starting with `ubuntu-pro-` followed by a version.
* `gcp.pro-fips`: names starting with `ubuntu-pro-fips-`. Both `fips` and
  `fips-updates` images count.

Old images are marked deprecated. A release whose images are all deprecated
is no longer offered.

[Find Ubuntu images on GCE](https://ubuntu.com/gcp/docs/google-how-to/gce/find-ubuntu-images/)
describes the same images.

### WSL

The Ubuntu Pro client is available on official WSL distributions. On a Windows
machine, list them from PowerShell:

```powershell
wsl --list --online
```

Each `Ubuntu-<version>` name is a release, such as `Ubuntu-24.04` for noble.
Ignore the unversioned `Ubuntu` entry, which tracks the latest LTS. Releases
that are not listed are not available on `wsl`.

Update the `wsl_releases` map in `features/cloud.py` to match, along with
`features/targets.yaml`.

### LXD

`lxd-container` and `lxd-vm` are not checked against a publisher. The tests
cover the releases in ESM, the supported releases (including interim)
and the development release. Check the releases in those categories:

```bash
ubuntu-distro-info --supported-esm
ubuntu-distro-info --supported
```

`lxd-container` and `lxd-vm` should include all the releases listed by those
two commands.

## Validate the change

```bash
tox -e tools-test
```

The tests load the real `features/targets.yaml`, so a malformed entry will raise
an error. Update `TestRepositoryData` if you changed a machine type's releases.
