# Raise the minimum Python version

Code that runs on target machines must work with the `python3` shipped by the
oldest Ubuntu release that the branch supports. On `main` that release is
16.04 Xenial, which ships Python 3.5. When the branch stops supporting its
oldest release, raise the minimum to the next release's Python version.

`tox -e vermin` enforces the minimum, and CI runs it in the static analysis
job.

## What the check covers

The check covers every Python file that runs on a target release. Code that
only runs on a developer's machine or in CI is left out. That includes the
behave tests in `features/` and most of `tools/`.

vermin scans the whole repository and skips only the paths excluded in the
`vermin` env in `tox.ini`. A new file is checked unless it sits under one of
those paths, so add a path there only when everything in it stays off target
machines.

The check is a quick first signal. The package builds and the integration
tests on the oldest release still run the code on its real `python3`.

## Find the new minimum

Look up the `python3` version of the new oldest release:

```shell
rmadison -u ubuntu -s bionic python3
```

```text
 python3 | 3.6.5-3 | bionic | amd64, arm64, armhf, i386, ppc64el, s390x
```

Use the major and minor version, `3.6` in this example.

## Update the check

1. In `tox.ini`, change `--target=3.5-` in the `vermin` env to the new
   version, for example `--target=3.6-`.
2. Run `tox -e vermin` and confirm it passes.

## Remove guards for the old version

Code can use a feature newer than the minimum only behind a guard, such as a
`try`/`except ImportError` with a fallback or a `sys.version_info` check.
vermin flags the newer feature even when it is guarded, so the guarded line
carries a `# novermin` comment. Those comments are how you find the guards
after raising the minimum:

```shell
git grep -n novermin -- ':!*.md'
```

If the new minimum provides the feature, remove the guard, the fallback and the
comment. Then run `tox -e vermin` and the unit tests again.
