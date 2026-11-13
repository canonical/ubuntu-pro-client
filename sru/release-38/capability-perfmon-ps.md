# Add capability `perfmon` to `ps` on Noble

## Scope

[LP #2148706](https://bugs.launchpad.net/ubuntu/+source/ubuntu-advantage-tools/+bug/2148706)
reports a boot-time denial on Ubuntu 24.04 (Noble), with
`apparmor` version `4.0.1really4.0.1-0ubuntu0.24.04.6` and
`ubuntu-pro-client` version `37.1ubuntu0~24.04`:

```text
apparmor="DENIED" operation="capable" class="cap" profile="ubuntu_pro_esm_cache//ps" comm="ps" capability=38 capname="perfmon"
```

The fix grants `perfmon` only in the `ps` child profile on Noble. All other
releases and child profiles are unchanged. As with the `cloud_id` and
`detect_virt` precedents, the fix is verified by CPC on an affected Noble
image rather than by unit tests.

## CPC Reproduction (Pending)

CPC must provide the affected image, architecture, pipeline configuration,
and exact reproduction steps in the Launchpad bug. Ask CPC whether other
releases are affected before extending the release condition.

The following is a proposed verification procedure, not CPC-provided
reproduction evidence:

1. Boot the affected Noble image with the reported package versions and run
   CPC's reproduction steps. Record the package versions and kernel version:

   ```sh
   dpkg-query -W apparmor ubuntu-pro-client
   uname -r
   sudo journalctl -k -b --no-pager | grep -F 'apparmor="DENIED"' | grep -F 'profile="ubuntu_pro_esm_cache//ps"'
   ```

2. Confirm that the output includes the reported `capname="perfmon"` denial.
3. Install the fixed Noble build, reboot, and repeat the same CPC steps and
   journal query. There must be no DENIED entries for this child profile in
   the new boot. Using `-b` excludes pre-fix entries without deleting logs.
4. Run CPC's image publication pipeline with the fixed build and retain its
   result. Other profiles' denials are outside this ticket's scope.

## CPC Confirmation (Pending)

Do not mark SRU verification complete until CPC confirms the result in
LP #2148706. Record the following here when available:

- CPC reproduction comment URL and affected image/configuration.
- CPC's assessment of whether releases other than Noble are affected.
- Fixed package version, image, and architecture tested.
- Before/after journal evidence and pipeline result.
- CPC confirmation comment URL and date.