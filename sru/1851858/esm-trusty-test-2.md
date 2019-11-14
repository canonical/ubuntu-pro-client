# Test case 2: Start from **pp64le** cloud-image on canonistack with u-a-t installed and esm attached, upgrade to -proposed and test architecture deltas

2.
 a. Start with a fresh Ubuntu **non-x86** instance which does have u-a-t installed. Enable esm with 'ubuntu-advantage attach'. Upgrade to u-a-t from -proposed.
 b. Confirm that machine remains attached, esm gets **disabled**, and status remains **disabled**.
 c. Update machine token files to represent delta in architectures from contract server. Ensure `ua refresh` retains attached, but esm status becomes **n/a**

```
#!/bin/bash
set -xe 
NOVARC=.canonistack/csmith.novarc
source $NOVARC

export UA_CONTRACT_TOKEN=<CONTRACT_TOKEN>
export ARCHIVE_URL=http://archive.ubuntu.com/ubuntu

# Assume only 1 keypair registered
export SSH_KEY=`openstack keypair list -f json | jq -r '.[0].Name'`
export LP_USER=<LP_USERNAME>

echo -- BEGIN test 2a: enable esm via "ubuntu-advantage attach <TOKEN>" on typical trusty-updates cloud-images which already have -updates installed

# Launch a basic trusty cloud-image that is updated to latest ubuntu-advantage-tools from -updates
cat > update-uat-trusty.yaml <<EOF
#cloud-config
ssh_import_id: [$LP_USER]
package_update: true
package_upgrade: true
runcmd:
 - apt-get install -qy ubuntu-advantage-tools 
EOF

if [ ! -e images-ppc64le.json ]; then
    echo "Creating image list for ppc64le"
    openstack image list --property architecture=ppc64le -f json > images-ppc64le.json
fi

sshopts=( -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o LogLevel=ERROR )

cat > ppa-key << EOF
-----BEGIN PGP PUBLIC KEY BLOCK-----

xo0EUs00cgEEAJJqaPue5gzQiLB1krT9slYbqVW/bSBpW9+qX8gFI44IVM/Bo3yh
9BPAs1RAzja96N0FS6SNlew4JYfk7MBT2sFDGpm3bTKt9Go7muO0JkvKv0vYgrrw
qORlWK3SfsYa6EpsCdVzZPAKvGzc8I0XywVgcJhM5okx+3J2naBaSp9NABEBAAHN
K0xhdW5jaHBhZCBQUEEgZm9yIENJIFRyYWluIFBQQSBTZXJ2aWNlIFRlYW3CuAQT
AQIAIgUCUs00cgIbAwYLCQgHAwIGFQgCCQoLBBYCAwECHgECF4AACgkQhVBBKOzx
IEy62gP/T2h98ongV+RXekM1DpgTNoH0PBHrZVj4zfrvrYKZOaxRmJ6TWtzG8tFI
uB4gPjaFeenJBhCFaZ9UncFQemS9jztQ/pA049L1N7Tijd8/BKD7gc7tM07+Fq+Q
6DT7VuUFiVlfZUwWYzk5UXEk6ctluoIRpnRWUHmh6NssuAgd1Nk=
=aPbC
-----END PGP PUBLIC KEY BLOCK-----
EOF

cat > add_uat_apt_pocket.sh << EOF
#/bin/bash
pocket_name=\$1
if [ "\$pocket_name" = "devel" ]; then
  echo deb [trusted=yes] http://ppa.launchpad.net/ci-train-ppa-service/3839/ubuntu trusty main | tee /etc/apt/sources.list.d/\$pocket_name.list
  apt-key add /ppa-key
else
  echo deb $ARCHIVE_URL \$pocket_name main | tee /etc/apt/sources.list.d/\$pocket_name.list
fi
EOF

cat > fake_contract_delta.sh << EOF
#!/bin/bash
echo "Introduce a fake architecture delta by modifying the cache machine token"
sed -i 's/"i386", "ppc64le",/"i386",/' /var/lib/ubuntu-advantage/private/machine-token.json
sed -i 's/"i386", "ppc64le",/"i386",/' /var/lib/ubuntu-advantage/private/machine-access-esm-infra.json
EOF


for series in trusty; do
  echo "### BEGIN $series"
  # Determine image, launch instance and attach IP address
  image=$(cat images-ppc64le.json | jq -r '.[]|select((.Name|contains("disk1.img")) and (.Name|contains("'$series'"))) | .ID' | tail -n 1)
  openstack server create --flavor cpu1-ram2-disk20 --image $image --key-name $SSH_KEY --user-data update-uat-trusty.yaml test-$series --wait
  sleep 10
  VM_IP=`openstack server show test-trusty -f json | jq -r '.addresses' | awk -F '=' '{print $NF}'`
  echo "Wait for cloud-init to finish startup on trusty: $VM_IP"
  RUNLEVEL="NOTSET"
  while ! [ "N 2" = "$RUNLEVEL" ]; do echo -n '.'; sleep 5; RUNLEVEL=`ssh "${sshopts[@]}" ubuntu@$VM_IP runlevel`; done; echo

  echo "Confirm u-a-t is already installed"
  ssh "${sshopts[@]}" ubuntu@$VM_IP -- apt-cache policy ubuntu-advantage-tools


# emit script to upgrade u-a-t
  scp "${sshopts[@]}" ppa-key ubuntu@$VM_IP:.
  scp "${sshopts[@]}" add_uat_apt_pocket.sh ubuntu@$VM_IP:.
  scp "${sshopts[@]}" fake_contract_delta.sh ubuntu@$VM_IP:.
  ssh "${sshopts[@]}" ubuntu@$VM_IP chmod 755 ./add_uat_apt_pocket.sh
  ssh "${sshopts[@]}" ubuntu@$VM_IP chmod 755 ./fake_contract_delta.sh
  echo "Enable esm via ubuntu-advantage enable-esm"
  ssh "${sshopts[@]}" ubuntu@$VM_IP -- sudo ua attach $UA_CONTRACT_TOKEN

  echo "Confirm python-jinja2 is available for esm PPA"
  ssh "${sshopts[@]}" ubuntu@$VM_IP apt-cache policy python-jinja2

  echo "Upgrade u-a-t to trusty-proposed"
  echo -- BEGIN test 2b: confirm machine stays attached, but esm is disabled after upgrade to -proposed
  ssh "${sshopts[@]}" ubuntu@$VM_IP -- sudo ./add_uat_apt_pocket.sh trusty-proposed
  ssh "${sshopts[@]}" ubuntu@$VM_IP -- sudo apt-get update;
  ssh "${sshopts[@]}" ubuntu@$VM_IP -- sudo apt-get install -y ubuntu-advantage-tools;

  echo "Confirm status remains attached: non-root"
  ssh "${sshopts[@]}" ubuntu@$VM_IP ua status;
  echo "Confirm status remains attached: root"
  ssh "${sshopts[@]}" ubuntu@$VM_IP sudo ua status;

  echo "Confirm python-jinja2 is available for esm PPA"
  ssh "${sshopts[@]}" ubuntu@$VM_IP apt-cache policy python-jinja2
  ssh "${sshopts[@]}" ubuntu@$VM_IP sudo apt-get install python-jinja2
  echo "Test 2c: Confirm deltas in architectures don't break ua client"
  ssh "${sshopts[@]}" ubuntu@$VM_IP sudo apt-get install python-jinja2
  ssh "${sshopts[@]}" ubuntu@$VM_IP sudo ./fake_contract_delta.sh
  ssh "${sshopts[@]}" ubuntu@$VM_IP sudo ua refresh
  ssh "${sshopts[@]}" ubuntu@$VM_IP sudo ua status
done
```
