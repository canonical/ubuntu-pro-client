# Demo

The 'demo' directory is reserved to developer environment test tools
and scripts. Nothing in this directory will be shipped as part of the
packaging.

## Files

- contract*patch: patch files applied to the generated demo Contract API service to create a sample API server: To be dropped when Contract Service API is functional
- demo-contract-service: script which will launch a new bionic lxc and install a https://github.com/CanonicalLtd/ua-service API backend with real PPA/livepatch credentials and sample response data
- entitlement-creds.json: Template file containing placeholders for esm, fips, fips-updates and livepatch credentials used in seeding ua-service API responses
- install-contract-server: script to be run within a newly launched lxc to patch and generate a ua-service openapi server with sample data
- run-uaclient: TODO
- runserver.sh: TODO
- uaclient: TODO
