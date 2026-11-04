# AGENTS.md

## Terminology

The keywords MUST, MUST NOT, SHOULD, SHOULD NOT and MAY describe the strength and meaning of instructions in this file and other agent files in this repo.

MUST -- This is a mandatory requirement. Follow it unless a higher-priority instruction from the user or execution environment directly conflicts with it.
MUST NOT -- This action is prohibited.
SHOULD -- This is the expected default. Deviate only when there is a clear, task-specific reason, and explain the deviation in the final response.
SHOULD NOT -- Avoid this action unless there is a clear, task-specific reason to do otherwise.
MAY -- This action is optional. Use judgment based on the task and surrounding code.

## Project overview

`ubuntu-pro-client` is a Python client that attaches Ubuntu machines to Ubuntu Pro and manages its services (ESM, Livepatch, FIPS, etc.). The `main` branch supports very old Ubuntu releases (back to 16.04 Xenial), so avoid modern-only syntax and dependencies. Xenial runs on Python 3.5.

- The target Python is the version shipped with supported Ubuntu releases (3.5); you MUST NOT assume the latest Python features are available.
- You MUST only use dependencies already declared in `requirements*.txt` / `setup.py`. You SHOULD NOT add new runtime dependencies unless there is strong justification.

## Repository layout

- `uaclient/` -- main Python source (CLI, API, entitlements, config, messages).
- `uaclient/tests/` and `uaclient/**/tests/` -- unit tests (pytest).
- `uaclient/messages/` -- user-facing strings (see string policy below).
- `features/` -- behave integration tests (`.feature` + step `.py` files).
- `apt-hook/`, `lib/`, `tools/`, `systemd/`, `update-motd.d/` -- supporting C++, shell, and helper code.
- `dev-docs/` -- developer how-to guides; `docs/` -- user documentation.
- `debian/` -- packaging, including `debian/po/` translations.

## Environment setup

The Python environment and dependencies SHOULD already be installed by `workshop`. You MUST flag any missing dependencies or tooling to the user.

## Common commands

Testing/linting is managed by `tox`.

Common environments:

- `tox -e test` -- unit tests (pytest).
- `tox -e test -- uaclient/tests/test_actions.py` -- a single test file.
- `tox -e flake8` -- Python linter.
- `tox -e mypy` -- type checker.
- `tox -e black` / `tox -e isort` -- formatting checks.
- `tox -e shellcheck` -- shell script linter.
- `tox -e reformat-gherkin` -- `.feature` file formatting.
- `tox -e behave` -- integration tests (slow; see below).

See `tox.ini` for the full list.

## Code style

- You MUST format with `black` and sort imports with `isort`.
- You MUST keep code compatible with Python 3.5 to preserve Xenial support.
- You SHOULD use type annotations and keep `tox -e mypy` clean.
- You SHOULD match existing patterns in the module you are editing and prefer small, focused changes over broad refactors.

## Testing instructions

- You MUST add or update unit tests for any code you change, and place them in the matching `tests/` directory.
- Tests MUST use pytest with `mock`/`unittest.mock`, and tests SHOULD be grouped in classes.
- `autouse` fixtures in `conftest.py` prevent host side effects and assume the process runs as root; you MUST rely on them rather than touching the real system.
- You MUST run `tox -e test` (and relevant lint envs) and ensure the suite is green before declaring a change complete.

### Integration (behave) tests

Integration tests launch real LXD/cloud instances and are slow. You SHOULD only run integration tests when specifically requested by the user.

## User-facing strings policy

Strings in `uaclient/messages/` are translated (see `debian/po/`). Changing an existing string MUST be justified in the PR (typo, factual error, or a product-driven wording change) and can affect translations. You SHOULD prefer adding a new string over editing an existing one when the meaning changes. See [dev-docs/explanation/string_changes_policy.md](dev-docs/explanation/string_changes_policy.md).

## Things to avoid

- You MUST NOT add new runtime dependencies or drop support for old Ubuntu releases.
- You MUST NOT edit `debian/changelog` version entries or packaging metadata unless the task is specifically a release/packaging change.
