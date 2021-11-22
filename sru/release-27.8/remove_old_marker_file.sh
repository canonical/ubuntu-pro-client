series=$1
deb=$2

set -e

GREEN="\e[32m"
RED="\e[31m"
BLUE="\e[36m"
END_COLOR="\e[0m"

function cleanup {
  lxc delete test --force
}

function on_err {
  echo -e "${RED}Test Failed${END_COLOR}"
  cleanup
  exit 1
}

trap on_err ERR

function print_and_run_cmd {
  echo -e "${BLUE}Running:${END_COLOR}" "$@"
  echo -e "${BLUE}Output:${END_COLOR}"
  lxc exec test -- sh -c "$@"
  echo
}

function explanatory_message {
  echo -e "${BLUE}$@${END_COLOR}"
}


explanatory_message "Starting $series container and updating ubuntu-advantage-tools"
lxc launch ubuntu-daily:$series test >/dev/null 2>&1
sleep 10

lxc exec test -- apt-get update >/dev/null
lxc exec test -- apt-get install -y ubuntu-advantage-tools >/dev/null
print_and_run_cmd "ua version"
explanatory_message "manually creating the marker file"
print_and_run_cmd "touch /var/lib/ubuntu-advantage/marker-license-check"
print_and_run_cmd "ls /var/lib/ubuntu-advantage"

explanatory_message "installing new version of ubuntu-advantage-tools from local copy"
lxc file push $deb test/tmp/ua.deb > /dev/null
print_and_run_cmd "dpkg -i /tmp/ua.deb"
print_and_run_cmd "ua version"


explanatory_message "make sure the marker file is not longer there"
print_and_run_cmd "ls /var/lib/ubuntu-advantage"
result=$(lxc exec test -- ls /var/lib/ubuntu-advantage)
echo "$result" | grep -v marker-license-check

echo -e "${GREEN}Test Passed${END_COLOR}"
cleanup
