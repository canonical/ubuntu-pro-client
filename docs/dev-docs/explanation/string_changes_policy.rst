.. _string_changes_policy:

Policy on changing user-facing strings in Ubuntu Pro Client
***********************************************************

As of version 30 of ``pro``, we support translations of user-facing strings
throughout the program. These are maintained in ``.po`` files in the
``debian/po`` directory of the git repository.

Whenever a string is changed, added, or deleted, this has an impact on existing
translations and therefore has an impact on the user experience of ``pro`` in
non-English locales.

To minimise regressions in translations, we implemented the following policy
regarding string changes. This policy is implemented in practice via a custom
GitHub action that posts a questionnaire and prompt for justification on all
GitHub PRs that modify the ``messages`` module of Ubuntu Pro Client.

Changing existing (already translated) strings
==============================================

All changes to existing strings require justification in the GitHub PR that
introduces the change.

Acceptable justifications:

* Typos: these should be minimal because of our spellcheck CI, but may still
  occur. Existing translations should be preserved when fixing typos.
* Factual errors: the nature of some features may change which will require us
  to update the description for accuracy.
* Change requested by a Product Manager due to the product being renamed or
  service descriptions being updated.

When a change is made to a translated string, we (Canonical) will endeavour to
provide translations for the changed string within the PR that introduces the
change. However, these translations are provided on a "best effort" basis and
we will not block the release of the changes due to incomplete translations.

Adding new (yet to be translated) strings
=========================================

New strings do not require extra justification.

Similarly to changed strings, a best effort attempt will be made to find
Canonical staff who can translate it prior to releasing; however, missing
translations will not block the release.

Deleting strings
================

Deleting strings do not require extra justification.

