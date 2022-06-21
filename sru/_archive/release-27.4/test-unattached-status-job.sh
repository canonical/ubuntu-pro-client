series=$1
set -x
lxc launch ubuntu-daily:$series test >/dev/null 2>&1
sleep 10

echo
echo "showing the network call in current ua version 27.3"
lxc exec test -- apt-get update >/dev/null
lxc exec test -- apt-get install -y ubuntu-advantage-tools >/dev/null
lxc exec test -- ua version
echo "disable all jobs but the status job"
lxc exec test -- ua config set metering_timer=0
lxc exec test -- ua config set update_messaging_timer=0
echo "run the status update timer job by removing current timer state and executing the timer script"
echo "and run tcpdump while executing the script, filtering by the current IPs of contracts.canonical.com"
lxc exec test -- rm -f /var/lib/ubuntu-advantage/jobs-status.json
lxc exec test -- sh -c "tcpdump \"(host 91.189.92.68 or host 91.189.92.69)\" & pid=\$! && sleep 5 && python3 /usr/lib/ubuntu-advantage/timer.py && kill \$pid"
echo "Verify that tcpdump saw packets in above output"
echo "Verify that the job was actually processed by the timer: update_status should be there."
lxc exec test -- grep "update_status" /var/lib/ubuntu-advantage/jobs-status.json


echo
echo
echo "installing new version from proposed"
lxc exec test -- sh -c "echo \"deb http://archive.ubuntu.com/ubuntu $series-proposed main\" | tee /etc/apt/sources.list.d/proposed.list"
lxc exec test -- apt-get update >/dev/null
lxc exec test -- sh -c "DEBIAN_FRONTEND=noninteractive apt-get install -o Dpkg::Options::=\"--force-confdef\" -o Dpkg::Options::=\"--force-confold\" -y ubuntu-advantage-tools" > /dev/null
lxc exec test -- ua version


echo "run the status update timer job by removing current timer state and executing the timer script"
echo "and run tcpdump while executing the script, filtering by the current IPs of contracts.canonical.com"
lxc exec test -- rm -f /var/lib/ubuntu-advantage/jobs-status.json
lxc exec test -- sh -c "tcpdump \"(host 91.189.92.68 or host 91.189.92.69)\" & pid=\$! && sleep 5 && python3 /usr/lib/ubuntu-advantage/timer.py && kill \$pid"
echo "Verify that tcpdump DID NOT see packets in above output"
echo "Verify that the job was actually processed by the timer: update_status should be there."
lxc exec test -- grep "update_status" /var/lib/ubuntu-advantage/jobs-status.json

lxc delete test --force
