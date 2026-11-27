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

## CPC Reproduction and verification (Pending)

CPC must provide the affected image, architecture, pipeline configuration,
and exact reproduction steps in the Launchpad bug. Ask CPC whether other
releases are affected before extending the release condition. 
CPC will confirm verification of the fix as well.