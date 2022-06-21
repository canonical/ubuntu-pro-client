#!/bin/sh

series=$1
name="test-systemd-$series"
DEB_PATH=$2

lxc launch ubuntu-daily:$series $name
sleep 5
lxc file push $DEB_PATH $name/tmp/ua.deb
echo "List timers in default state"
echo "--------------------------"
lxc exec $name -- sudo systemctl list-timers --all
echo "--------------------------"
echo "Disabling ua-messaging.timer"
echo "--------------------------"
lxc exec $name -- sudo systemctl stop ua-messaging.timer
lxc exec $name -- sudo systemctl disable ua-messaging.timer
lxc exec $name -- sudo systemctl list-timers --all
sleep 2
echo "--------------------------"
echo "Installing new UA package"
echo "--------------------------"
lxc exec $name -- sudo dpkg -i /tmp/ua.deb
echo "--------------------------"
echo "Verifying ua-timer.timer is disabled"
lxc exec $name -- sudo systemctl list-timers --all
echo "--------------------------"
lxc delete $name --force
