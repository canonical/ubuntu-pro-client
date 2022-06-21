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
lxc exec test -- apt-get install -y ubuntu-advantage-tools locate >/dev/null
print_and_run_cmd "ua version"
explanatory_message "Start the timer to make sure its state is fixed on upgrade"
print_and_run_cmd "systemctl start ua-license-check.timer"
print_and_run_cmd "systemctl status ua-license-check.timer"

explanatory_message "installing new version of ubuntu-advantage-tools from local copy"
lxc file push $deb test/tmp/ua.deb > /dev/null
print_and_run_cmd "dpkg -i /tmp/ua.deb"
print_and_run_cmd "ua version"

explanatory_message "systemd should not list the timer as failed"
print_and_run_cmd "systemctl status ua-license-check.timer || true"
print_and_run_cmd "systemctl --no-pager | grep ua-license-check || true"
result=$(lxc exec test -- sh -c "systemctl --no-pager | grep ua-license-check.timer" || true)
echo "$result" | grep -qv "ua-license-check.timer\s\+not-found\s\+failed"

echo -e "${GREEN}Test Passed${END_COLOR}"
cleanup
