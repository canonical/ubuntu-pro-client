### What happens during attach
After running the command `ua attach TOKEN`, UA will perform the following steps:

* read the config from /etc/ubuntu-advantage/uaclient.conf to obtain
  the contract\_url (default: https://contracts.canonical.com)
* POSTs to the Contract Server API @
  <contract_url>/api/v1/context/machines/token providing the \<contractToken\>
* The Contract Server responds with a JSON blob containing an unique machine
  token, service credentials, affordances, directives and obligations to allow
  enabling and disabling Ubuntu Advantage services
* UA client writes the machine token API response to the root-readonly
  /var/lib/ubuntu-advantage/private/machine-token.json
* UA client auto-enables any services defined with
  `obligations:{enableByDefault: true}`
