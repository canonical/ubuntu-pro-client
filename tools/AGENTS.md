# AGENTS.md (tools/)

This file adds to the root `AGENTS.md` for work under `tools/`. Terminology (MUST, SHOULD, ...) is defined there.

`tools/` holds development, CI and release helpers. They are not part of the `uaclient` package, but some take part in the package build: `debian/rules` runs `check-versions-are-consistent.py`, and `ua.bash` ships as bash completion.

## Layout

- A tool SHOULD be one file. A tool that needs more files (helper modules, tests, fixtures) SHOULD keep all of them in its own `tools/<name>/` directory.
- When another program imports a tool's module (for example, as a plugin), you MUST add only that tool's directory to the program's import path, never the repository root or `tools/`. Scripts that import `uaclient` or `features` from the repository root are exempt.
- You SHOULD keep the file list in `tools/README.md` up to date.

## Packaging and build

- You MUST NOT add `tools/__init__.py`. `find_packages` in `setup.py` would then ship `tools/` and every package under it.
- The package build runs a bare `python3 -m pytest` with no network and no tox. `testpaths = uaclient` in `tox.ini` limits it to the package tests. You MUST NOT make that run collect tests under `tools/`.
- The root rule on Python 3.5 compatibility covers only code that ships in the package. Under `tools/`, only `ua.bash` ships. Python tools that run during the package build MUST still work with the oldest supported release's Python and with only the build dependencies. Other tools MAY use the Python of the hosts they run on.
- You MUST NOT add a tool's dependencies to `requirements.test.txt`, because `setup.py` turns it into package test requirements. Declare them in the tox env that runs the tool or its tests.

## Testing

- Tool tests MUST run as part of the default `tox -e test`, so that CI runs them on every PR. That env collects every test under `tools/`, so you MUST NOT exclude them from it.
- You MUST NOT make tests opt-in through custom environment variables. If tests are too slow for the default run, first make them faster. A gate MUST be a registered pytest marker, used only for a substantial cost, and CI MUST still run the marked tests.
- A tool's tests SHOULD include end-to-end tests that run the real program the tool drives, so they show that the tool works. Use fakes or mocks for cases the real program cannot produce cheaply.
- The autouse fixtures in `uaclient/conftest.py` do not apply under `tools/`. Tests MUST keep their side effects inside temporary directories.

## Linting

- The lint envs in `tox.ini`, which CI runs, do not check `tools/`, except shellcheck for `tools/*.sh`. The pre-commit hooks (black, isort, reformat-gherkin, shellcheck) do check `tools/`, so your changes there MUST pass them. Shell scripts MUST stay at `tools/*.sh`, or you MUST extend the shellcheck glob to cover them.

## Design

- You SHOULD use the wrapped program's own extension points (plugins, formatters, config, its native output formats) rather than bespoke side channels such as custom environment variables, extra files for the tool to parse, or monkeypatching.
