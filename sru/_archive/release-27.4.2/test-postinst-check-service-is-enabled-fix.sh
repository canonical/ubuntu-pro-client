series=$1
name=test-$series
set -x
lxc launch ubuntu-daily:$series $name >/dev/null 2>&1
sleep 3

echo "Confirming we are runnign a ${series} machine"
lxc exec $name -- lsb_release -a

echo "Updating to the latest version of UA"
lxc exec $name -- apt-get update >/dev/null
lxc exec $name -- apt-get install -y ubuntu-advantage-tools >/dev/null
lxc exec $name -- ua version
echo "Running ua status to persist cache"
lxc exec $name -- ua status
echo "Modifying ESM_SUPPORTED_ARCHS to emulate the issue"
lxc exec $name -- sed -i "s/ESM_SUPPORTED_ARCHS=\"i386 amd64\"/ESM_SUPPORTED_ARCHS=\"\"/" /var/lib/dpkg/info/ubuntu-advantage-tools.postinst
echo "Re-running the postinst script. Confirming that KeyError is reported on stdout"
lxc exec $name -- dpkg-reconfigure ubuntu-advantage-tools

echo "Updating UA to the version with the fix"
lxc exec $name -- sh -c "echo \"deb http://archive.ubuntu.com/ubuntu $series-proposed main\" | tee /etc/apt/sources.list.d/proposed.list"
lxc exec $name -- apt-get update >/dev/null
lxc exec $name -- apt-get install -y ubuntu-advantage-tools >/dev/null
lxc exec $name -- ua version

echo "Running ua status to persist cache"
lxc exec $name -- ua status
echo "Modifying ESM_SUPPORTED_ARCHS to emulate the issue"
lxc exec $name -- sed -i "s/ESM_SUPPORTED_ARCHS=\"i386 amd64\"/ESM_SUPPORTED_ARCHS=\"\"/" /var/lib/dpkg/info/ubuntu-advantage-tools.postinst
echo "Re-running the postinst script. Confirming that KeyError is no longer reported"
lxc exec $name -- dpkg-reconfigure ubuntu-advantage-tools

lxc delete --force $name
