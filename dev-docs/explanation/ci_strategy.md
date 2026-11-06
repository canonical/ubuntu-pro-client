# CI strategy

Every PR merged through the merge queue passes the full integration test suite
first, whether the PR comes from a branch in this repository or from a fork.
To keep feedback fast, CI works in two stages:

* **Fast checks** run on every push to a PR. They include static analysis,
  unit tests and package builds, and they need no secrets.
* **The full suite** runs in the
  [GitHub merge queue](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/configuring-pull-request-merges/managing-a-merge-queue),
  after the PR is approved and queued. It includes the integration tests.

## Why integration tests wait for the merge queue

The integration tests need secrets, such as contract tokens. GitHub does not
give secrets to workflow runs for PRs from forks, so those PRs cannot run the
integration tests directly. Merge queue builds run inside this repository, so
they have access to the secrets.

Code only reaches the queue after a team member has reviewed and approved it,
as described in the [PR review policy](pr_review_policy.md). The approval must
cover the most recent push, so code added after the review cannot reach the
queue. That review is what makes it safe to run the code with secrets.

Running the integration tests in the queue also means:

* Every PR follows the same path, whatever repository it comes from.
* The integration tests run against the code exactly as it will land on
  `main`. The queue merges the commit it tested, so a push made while the PR
  is queued does not land.

## How the queue tests PRs

The queue tests each PR on top of `main` and every PR queued ahead of it. When
that run fails, the queue removes the PR and tests the PRs behind it again
without it. A failure reported on a PR can therefore come from how its change
combines with a PR queued ahead of it.

## One required check

Branch protection requires one check: the gate. The gate checks the result of
every other job, with rules that depend on what started the run:

* On a PR, the fast checks must pass and the integration tests must not run.
* In the merge queue and on manual runs, the fast checks and the integration
  tests must all pass.
* On a push to `main` or a release branch, the fast checks must pass and the
  integration tests must not run.

A passing gate on a PR covers only the fast checks.

The gate uses explicit rules for each kind of run because GitHub treats a
skipped job as a passing required check. Without them, an integration run that
was skipped by mistake in the merge queue would look like a pass.

Because only the gate is required, jobs can be added, renamed or split
without changes to branch protection.

## Changes that bypass the queue

CI runs the fast checks on every push to `main` and to release branches. This
covers changes that reach those branches without passing through the merge
queue, such as a merge that bypasses it.

Release branches have no merge queue. CI runs the integration tests on a
release branch only when a team member starts a manual run.

## Manual runs

Team members, who have write access to this repository, can start the full
suite by hand on any of its branches, for example to debug a failure before a
PR is queued. Manual runs have access to the secrets because they run inside
this repository.
