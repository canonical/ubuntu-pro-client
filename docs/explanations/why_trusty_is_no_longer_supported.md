# Why trusty is no longer supported ?

Right now, the Ubuntu Advantange Client (UA) package is not longer being updated for Trusty
releases. Right now, there is no compelling commercial needs to justify the engineering effort
to update the UA package for Trusty. Specially because Trusty already has access through older
version of UA to `esm-infra` and `livepatch`, which are services most Trusty users will already
benefit from. However, if our team identifies any critical CVEs related specifically to UA on
Trusty that need solving, we can provide one-off fixes/backports for those issues.
