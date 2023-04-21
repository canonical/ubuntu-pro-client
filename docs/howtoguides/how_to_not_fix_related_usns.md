# How to not fix related USNs

When running the `pro fix` command for a USN, by default we also try to fix
any related USNs as well. To better understand the concept of related USNs,
you can refer to our [related USNs guide](../explanations/cves_and_usns_explained.md).
To make this clear, let's take a look into the following example:

```
USN-5573-1: rsync vulnerability
Found CVEs:
  - https://ubuntu.com/security/CVE-2022-37434

Fixing requested USN-5573-1
1 affected source package is installed: rsync
(1/1) rsync:
A fix is available in Ubuntu standard updates.
{ apt update && apt install --only-upgrade -y rsync }

✔ USN-5573-1 is resolved.

Found related USNs:
- USN-5570-1
- USN-5570-2

Fixing related USNs:
- USN-5570-1
No affected source packages are installed.

✔ USN-5570-1 does not affect your system.

- USN-5570-2
1 affected source package is installed: zlib
(1/1) zlib:
A fix is available in Ubuntu standard updates.
{ apt update && apt install --only-upgrade -y zlib1g }

✔ USN-5570-2 is resolved.

Summary:
✔ USN-5573-1 [requested] is resolved.
✔ USN-5570-1 [related] does not affect your system.
✔ USN-5570-2 [related] is resolved.
```

We can see here that the `pro fix` command fixed the requested **USN-5573-1** while also
handling both **USN-5570-1** and **USN-5570-2**, which are related to the requested USN.
If you don't want to fix any related USNs during the `fix` operation, just use the
`--no-related` flag. By running the command `pro fix USN-5573-1 --no-related` we would get
the following output instead:

```
USN-5573-1: rsync vulnerability
Found CVEs:
  - https://ubuntu.com/security/CVE-2022-37434

Fixing requested USN-5573-1
1 affected source package is installed: rsync
(1/1) rsync:
A fix is available in Ubuntu standard updates.
{ apt update && apt install --only-upgrade -y rsync }

✔ USN-5573-1 is resolved.
```

Note that we have not analysed or tried to fix any related USNs
