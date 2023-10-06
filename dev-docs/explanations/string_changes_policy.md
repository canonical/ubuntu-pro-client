# Policy on changing user-facing strings in Ubuntu Pro Client

As of version 30 of `pro`, we support translations of user-facing strings throughout the program.
These are maintained in `po` files in the `debian/po` directory of the git repository.
Whenever a string is changed, added, or deleted, that has an impact on existing translations and
therefore an impact on the user experience of `pro` in non-english locales.
To minimize regressions in translations, we have the following policy in place regarding string changes.
This policy is implemented in practice via a custom GitHub action that posts a questionnaire and prompt
for justification on all GitHub PRs that modify the `messages` module of Ubuntu Pro Client.

## Changing existing (already translated) strings

All changes to existing strings will require justification in the GitHub PR that introduces the change.

Acceptable justifications:
- Typos: these will hopefully be minimal after adding spell-check CI, but still could occur.
  - Note: existing translations should be preserved when fixing typos
- Factual errors: the nature of some features may change which will require us to update the description so that it is not wrong.
- A Product Manager told us to change it: E.g. Product is renamed or description needs more info.

When a change is made to a translated string, a best effort will be made to get Canonicalers to fix the translations of the changed string in the PR that introduces the change. However, a lack of complete translation replacements will not block the release of the changes.

## Adding new (yet to be translated) strings

New strings do not require extra justification. Similarly to changed strings, a best effort will be made to get Canonicalers to translate it prior to releasing; however, missing translations will not block the release.

## Deleting strings

Deleting strings will be okay without extra justification.

