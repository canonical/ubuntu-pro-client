# Terminology

The following vocabulary is used to describe different aspects of the work
Ubuntu Advantage Client performs:

| Term     | Meaning |
| -------- | -------- |
| UA Client | The python command line client represented in this ubuntu-advantage-client repository. It is installed on each Ubuntu machine and is the entry-point to enable any Ubuntu Advantage commercial service on an Ubuntu machine. |
| Contract Server | The backend service exposing a REST API to which UA Client authenticates in order to obtain contract and commercial service information and manage which support services are active on a machine.|
| Entitlement/Service | An Ubuntu Advantage commercial support service such as FIPS, ESM, Livepatch, CIS-Audit to which a contract may be entitled |
| Affordance | Service-specific list of applicable architectures and Ubuntu series on which a service can run |
| Directives | Service-specific configuration values which are applied to a service when enabling that service |
| Obligations | Service-specific policies that must be instrumented for support of a service. Example: `enableByDefault: true` means that any attached machine **MUST** enable a service on attach |
