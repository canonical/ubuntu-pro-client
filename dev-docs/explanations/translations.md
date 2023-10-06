# Translations

Ubuntu Pro Client is a special package in Ubuntu: it is updated frequently in all Ubuntu LTS releases.
That makes language packs unsuitable for providing and updating translations for Ubuntu Pro Client.

In addition, Ubuntu Pro Client includes lots of language with potential commercial and contractual
implications related to Canonical's Ubuntu Pro offering. That means we need to maintain tight control
over the language used in all messages.

## How are translations delivered and updated?

Normally, packages in `main` are translated via language packs; however language packs are only updated
in stable releases around the time of point releases. If Ubuntu Pro translations were put in the language pack,
then the language pack wouldn’t get updated as we continue to SRU new Ubuntu Pro Client versions back to
old Ubuntu releases. That would cause the translations provided by the language pack to drift out of sync with
the version of Ubuntu Pro Client installed.

Because of this, Ubuntu Pro Client is not included in the Ubuntu language pack and instead ships all translations
directly in our own source package. However, translations are kept in a separate binary package so that it is not
required to be installed with Ubuntu Pro Client (and therefore not required in `ubuntu-minimal`). Translations are
in a binary package named: `ubuntu-pro-client-l10n`.
The `ubuntu-advantage-tools` binary package _Recommends_ `ubuntu-pro-client-l10n`, but doesn't require it.

In order to ship translation files (`.mo` files) in the `ubuntu-pro-client-l10n` binary package, this package is
explicitly excluded from language pack translation stripping done by the `pkgbinarymangler` package
(see [LP: #2037584](https://bugs.launchpad.net/ubuntu/+source/pkgbinarymangler/+bug/2037584)).

## How are translations maintained and added?

Translations live as `.po` files in the `debian/po/` directory.

Because many of the Pro Client’s messages are commercial in nature, a bad translation could potentially have odd or
misleading contractual implications. Because of that, we generally want all translations to come from Canonical employees.

Regarding contributions, we will:
- Accept Canonical-employee PRs of translations in GitHub.
- Consider community bugs/issues regarding translation wording/suggestions.
  - We’ll get input from a Canonical employee who speaks the language in question.
- **Not** accept community PRs directly changing translations.

We generally will not support translations to a language that no Canonical-employee understands and is willing to review/help maintain.

We will set up a project on https://translations.launchpad.net where only Canonical employees have permission to contribute
translations to Ubuntu Pro Client. Before every release of Ubuntu Pro Client, we will download the latest translations
from this Launchpad project and integrate them. *Note that this is not done yet.*

## What parts of the Pro Client will get translated?

These **do** get translated:
- Human-readable output of all `pro` CLI commands, including:
    - help text (called out because this is handled in a special way in Pro Client)
    - `pro status` table values including: “enabled”, ”disabled”, “available”, etc
- Pro-related messages inserted into `apt upgrade`
- Messages inserted into the MOTD

These do **not** get translated:
- JSON output of `pro` CLI commands
  - For example: {“status”: “enabled”} – both “status” and “enabled” should remain in English
  - Exception: some values in the JSON are messages intended for humans – these should get translated
- CLI flags
- Logs
- APT News

We would like translate these, but we’re considering them out of scope for now:
- manpage
