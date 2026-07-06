# AGENTS.md

## Project overview

`ubuntu-pro-client` (the `pro` command, package `ubuntu-advantage-tools`) is a Python client that attaches Ubuntu machines to Ubuntu Pro and manages its services (ESM, Livepatch, FIPS, etc.). The `main` branch supports very old Ubuntu releases (back to 16.04 Xenial), so avoid modern-only syntax and dependencies. Xenial runs on Python 3.5.

- Target Python is the version shipped with supported Ubuntu releases; do not assume the latest Python features are available.
- Only use dependencies already declared in `requirements*.txt` / `setup.py`. Do not add new runtime dependencies without strong justification.

## Repository layout

- `uaclient/` -- main Python source (CLI, API, entitlements, config, messages).
- `uaclient/tests/` and `uaclient/**/tests/` -- unit tests (pytest).
- `uaclient/messages/` -- user-facing strings (see string policy below).
- `features/` -- behave integration tests (`.feature` + step `.py` files).
- `apt-hook/`, `lib/`, `tools/`, `systemd/`, `update-motd.d/` -- supporting C++, shell, and helper code.
- `dev-docs/` -- developer how-to guides; `docs/` -- user documentation.
- `debian/` -- packaging, including `debian/po/` translations.

## Environment setup

The Python environment and dependencies should already be installed by `workshop`. Flag any missing dependencies or tooling to the user.

## Common commands

Run all lint + unit checks (matches CI defaults):

```bash
tox
```

Individual environments (see `tox.ini` for the full list):

- `tox -e test` -- unit tests (pytest).
- `tox -e test -- uaclient/tests/test_actions.py` -- a single test file.
- `tox -e flake8` -- Python linter.
- `tox -e mypy` -- type checker.
- `tox -e black` / `tox -e isort` -- formatting checks.
- `tox -e shellcheck` -- shell script linter.
- `tox -e reformat-gherkin` -- `.feature` file formatting.
- `tox -e behave` -- integration tests (slow; see below).

## Code style

- Format with `black` and sort imports with `isort`
- Keep code compatible with Python 3.5 to keep support for Xenial
- Use type annotations and keep `tox -e mypy` clean.
- Match existing patterns in the module you are editing; prefer small, focused changes over broad refactors.

## Testing instructions

- Add or update unit tests for any code you change; put them beside the code in the matching `tests/` directory.
- Tests use pytest with `mock`/`unittest.mock`. Tests are grouped in classes.
- `autouse` fixtures in `conftest.py` prevent host side effects and assume the process runs as root -- rely on them rather than touching the real system.
- Always run `tox -e test` (and the relevant lint envs) and make the suite green before declaring a change complete.

### Integration (behave) tests

Integration tests launch real LXD/cloud instances and are slow. Integration tests should only be run when they are specifically requested by the user.

## User-facing strings policy

Strings in `uaclient/messages/` are translated (see `debian/po/`). Changing an existing string requires justification in the PR (typo, factual error, or a product-driven wording change) and can affect translations. Prefer adding a new string over editing an existing one when the meaning changes. See [dev-docs/explanation/string_changes_policy.md](dev-docs/explanation/string_changes_policy.md).

## Things to avoid

- Do not add new runtime dependencies or drop support for old Ubuntu releases.
- Do not edit `debian/changelog` version entries or packaging metadata unless the task is specifically a release/packaging change.
