# Tools

The 'tools' directory is reserved for development, CI and release tools and
scripts. Apart from `ua.bash`, nothing in this directory is shipped as part of
the packaging.

## Files

- apidocgen.py: Generate RST documentation for API endpoints
- behave_rerun/: Run behave in CI and rerun only the failed scenarios, to absorb flaky tests
- build.py: Build the package from the current directory
- build.sh: Shell entrypoint for the build script
- check-versions-are-consistent.py: Helper script to verify changelog and package version matches.
- clidocgen.py: Generate documentation for the CLI commands
- create-gh-release-branches.sh: Generate the stable release branches, after the devel branch is ready
- process_logs.py: Parse and filter the Pro client log file
- README.md: This file.
- refresh-keyrings.sh: Refresh the keyring files for services, stored in the repo
- setup_sbuild.sh: Downloads and prepares chroots used in the build (and test) process.
- spellcheck-allowed-words.txt: Extra words accepted by the hunspell check of user-facing messages in CI
- test-in-lxd.sh: Build the package and then install it on an LXD instance for testing
- test-in-multipass.sh: Build the package and then install it on a multipass instance for testing
- ua.bash: Bash completion script for `ua` | `pro`
- update-pos.sh: Regenerate the translation template and update the `.po` files in `debian/po`
