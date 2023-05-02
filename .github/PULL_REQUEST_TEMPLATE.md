## Why is this needed?
<!-- This information should be captured in your commit messages, so any description here can be very brief -->
This PR solves all of our problems because...

<!--
By default, we rebase PRs and will ask for a clean well-organized commit history in the PR before rebasing.
If your PR is small enough and you prefer, uncomment the following section and fill it out to request a squashed PR.
-->
<!--
## Please Squash this PR with this commit message

```
summary: no more than 70 characters

A description of what the change being made is and why it is being
made, if the summary line is insufficient.  The blank line above is
required. This should be wrapped at 72 characters, but otherwise has
no particular length requirements.

If you need to write multiple paragraphs, feel free.

LP: #NNNNNNN (replace with the appropriate Launchpad bug reference if applicable)
Fixes: #NNNNNNN (replace with the appropriate github issue if applicable)
```
-->

## Test Steps
<!-- Please include any steps necessary to verify (and reproduce if
this is a bug fix) this change on a live deployed system,
including any necessary configuration files, user-data,
setup, and teardown. Scripts used may be attached directly to this PR. -->

<!-- Example:
```
env SHELL_BEFORE=1 ./tools/test-in-lxd.sh xenial
# Set up test scenario before upgrade
exit # new version gets installed after exit and lxc shell is re-started
sudo pro new-sub-command --new-flag
# Assert something
```
-->

## Checklist
<!-- Go over all the following points, and put an `x` in all the boxes
that apply. -->
 - [ ] I have updated or added any unit tests accordingly
 - [ ] I have updated or added any integration tests accordingly
 - [ ] I have updated or added any documentation accordingly

## Does this PR require extra reviews?
<!-- Should people outside of the team see and approve these changes before the
PR gets merged? If yes, make sure to tag them as reviewers. -->
 - [ ] Yes
 - [ ] No
