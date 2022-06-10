x_deb=$1
b_deb=$2
series=bionic

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
lxc exec test -- apt-get install -y ubuntu-advantage-tools locate >/dev/null
explanatory_message "installing xenial version of ubuntu-advantage-tools from local copy"
lxc file push $x_deb test/tmp/uax.deb > /dev/null
print_and_run_cmd "dpkg -i /tmp/uax.deb"
print_and_run_cmd "ua version"

explanatory_message "Note where all cloud-id-shim artifacts are before upgrade"
print_and_run_cmd "updatedb"
print_and_run_cmd "locate ubuntu-advantage-cloud-id-shim"

explanatory_message "installing bionic version of ubuntu-advantage-tools from local copy"
lxc file push $b_deb test/tmp/uab.deb > /dev/null
print_and_run_cmd "dpkg -i /tmp/uab.deb"
print_and_run_cmd "ua version"

explanatory_message "cloud-id-shim artifacts should be gone"
print_and_run_cmd "updatedb"
print_and_run_cmd "locate ubuntu-advantage-cloud-id-shim || true"
result=$(lxc exec test -- locate ubuntu-advantage-cloud-id-shim || true)
test -z "$result"

echo -e "${GREEN}Test Passed${END_COLOR}"
cleanup
