series=$1
deb=$2

set -eE

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

explanatory_message "Check that log is not world readable"
print_and_run_cmd "ua version"
print_and_run_cmd "head /var/log/ubuntu-advantage.log"
print_and_run_cmd "find /var/log/ -name ubuntu-advantage.log -perm 0600 | grep -qz ."

lxc exec test -- apt-get update >/dev/null
explanatory_message "installing new version of ubuntu-advantage-tools from local copy"
lxc file push $deb test/tmp/ua.deb > /dev/null
print_and_run_cmd "dpkg -i /tmp/ua.deb"
print_and_run_cmd "ua version"

explanatory_message "Check that log files permissions are still the same"
print_and_run_cmd "find /var/log/ -name ubuntu-advantage.log -perm 0600 | grep -qz ."

explanatory_message "Check that logrotate command will create world readable files"
print_and_run_cmd "logrotate --force /etc/logrotate.d/ubuntu-advantage-tools"
print_and_run_cmd "find /var/log/ -name ubuntu-advantage.log -perm 0644 | grep -qz ."
print_and_run_cmd "find /var/log/ -name ubuntu-advantage.log.1 -perm 0600 | grep -qz ."

explanatory_message "Check that running logrotate again will stil make world readable files"
# Just to add new entry to the log
print_and_run_cmd "ua version"
print_and_run_cmd "logrotate --force /etc/logrotate.d/ubuntu-advantage-tools"
print_and_run_cmd "find /var/log/ -name ubuntu-advantage.log -perm 0644 | grep -qz ."
print_and_run_cmd "find /var/log/ -name ubuntu-advantage.log.1 -perm 0644 | grep -qz ."
print_and_run_cmd "find /var/log/ -name ubuntu-advantage.log.2.gz -perm 0600 | grep -qz ."

echo -e "${GREEN}Test Passed${END_COLOR}"
cleanup
