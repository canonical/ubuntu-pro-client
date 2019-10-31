# Test case 1: Attach a trusty machine and verify ESM is attached and ESM packages can be installed.
```
#!/bin/bash
echo "--- Test 1: Attach a trusty machine using a token from auth.contracts.canonical.com and verify ESM is attached and ESM packages can be installed."

echo "Launch Trusty container with allowing ssh access for <LP_ID>"

export CONTRACT_TOKEN="<contractToken>"
export ARCHIVE_URL="http://archive.ubuntu.com/ubuntu"

cat >trusty-ssh.yaml <<EOF
#cloud-config
ssh_import_id: [chad.smith]
EOF
lxc launch ubuntu-daily:trusty sru-trusty -c user.user-data="$(cat trusty-ssh.yaml)"

echo "Wait for cloud-init to finish startup on trusty"
RUNLEVEL="NOTSET"
while ! [ "N 2" = "$RUNLEVEL" ]; do echo -n '.'; sleep 1; RUNLEVEL=`lxc exec sru-trusty runlevel`; done; echo

# emit script to upgrade u-a-t
cat > add_uat_apt_pocket.sh << EOF
#/bin/bash
pocket_name=\$1
echo deb $ARCHIVE_URL \$pocket_name main | tee /etc/apt/sources.list.d/\$pocket_name.list
EOF

echo "Upgrade ubuntu-advantage-tools to trusty-proposed"
lxc file push add_uat_apt_pocket.sh sru-trusty/;
lxc exec sru-trusty chmod 755 /add_uat_apt_pocket.sh;
lxc exec sru-trusty /add_uat_apt_pocket.sh trusty-proposed;
lxc exec sru-trusty -- apt-get update -q;
lxc exec sru-trusty -- apt-get install -qy ubuntu-advantage-tools;

echo "Confirm ubuntu-advantage-tools version from -proposed"
lxc exec sru-trusty -- apt-cache policy ubuntu-advantage-tools;


echo "Enable esm on trusty as non-root sudo"
VM_IP=`lxc list sru-trusty -c 4 | awk '/10/{print $2}'`

# Expect ua status to show esm enabled, livepatch n/a
ssh ubuntu@$VM_IP -- sudo ua attach $CONTRACT_TOKEN

echo "Confirm ansible is available for trusty esm PPA"
ssh ubuntu@$VM_IP -- apt-cache policy ansible

ANSIBLE_ESM_VER=`lxc exec sru-trusty -- apt-cache policy ansible | grep esm | grep Candidate | awk '{print $2}'`

echo "Installing ansible from esm"
ssh ubuntu@$VM_IP -- sudo apt-get install ansible=$ANSIBLE_ESM_VER -y
```
