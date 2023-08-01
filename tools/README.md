# Tools

The 'tools' directory is reserved for test tools and scripts. Nothing
in this directory will be shipped as part of the packaging

## Files

- build.py: Build the package from the current directory
- build.sh: Shell entrypoint for the build script
- create-lp-release-branches.sh: Generate the stable release branches on Launchpad, after the devel branch is ready
- check-versions-are-consistent.py: Helper script to verify changelog and package version matches.
- README.md: This file.
- refresh-keyrings.sh: Refresh the keyring files for services, stored in the repo
- run-integration-tests.py: Python entrypoint for the `tox -e behave` commands.
- setup_sbuild.sh: Downloads and prepares chroots used in the build (and test) process.
- test-in-lxd.sh: Build the package and then install it on an LXD instance for testing
- test-in-multipass.sh: Build the package and then install it on a multipass instance for testing
- ua.bash: Bash completion script for `ua` | `pro`
- ua-test-credentials.example.yaml: Template for inserting your own test
credentials - make a copy and/or remove `'.example'` to use it in `run-integration-tests.py`
