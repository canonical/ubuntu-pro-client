# PR review policy

The team follows this policy for PR reviews:

* Simple PRs: PRs that fix typos or perform one line changes require **one** approval from a team
  member and can be merged immediately by the reviewer.
* Low complexity PRs: For short PRs we require **one** approval to merge. However, after approving the
  PR we will wait for **one** day before merging it. This will allow other team members to review
  the PR if they want. When one day has passed after the approval and there are no new requested
  changes, any team member can merge.
* Complex PRs: Minimum of **two** approvals from team members. After there are two team-member approvals
  and there are no remaining requested changes, any team member can merge.
* SRU blocker PRs: Some PRs may also require review from members that are not on the team, like SRU
  reviewers. This is the case, for example, when adding/creating new systemd units. For those PRs, we
  will directly ask for feedback from members outside the team that have a more suitable background to review
  the change we are proposing. Therefore, we not only require at least **two** approvals from team members,
  but also approvals from every external reviewer we assigned. After the required approvals have been given,
  the additional review feedback has been taken into account, and there are no requested changes remaining,
  any team member can merge.
