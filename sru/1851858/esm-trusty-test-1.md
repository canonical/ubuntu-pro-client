# Test case 1: Start from x86_64 cloud-image with u-a-t installed and esm attached, upgrade to -proposed

1.
 a. Start with a fresh Ubuntu **x86_64** instance which does have u-a-t installed. Enable esm with 'ubuntu-advantage attach'. Upgrade to u-a-t from -proposed.
 b. Confirm that machine remains attached, esm enabled and package installs
    work
 c. Confirm that machine handles ua-contract architecture deltas for esm and remains attached/enabled

```
export UA_CONTRACT_TOKEN=<NewContractToken>
export ARCHIVE_URL=http://archive.ubuntu.com/ubuntu

echo -- BEGIN test 1a: enable esm via "ubuntu-advantage attach <TOKEN>" on typical trusty-updates cloud-images which already have -updates installed

# Launch a basic trusty cloud-image that is updated to latest ubuntu-advantage-tools from -updates
cat > update-uat-trusty.yaml <<EOF
#cloud-config
package_update: true
package_upgrade: true
runcmd:
 - apt-get install -qy ubuntu-advantage-tools 
EOF

cat > fake_contract_delta.sh << EOF
#!/bin/bash
echo "Introduce a fake architecture delta by modifying the cache machine token"
sed -i 's/"i386", "ppc64le",/"i386",/' /var/lib/ubuntu-advantage/private/machine-token.json
sed -i 's/"i386", "ppc64le",/"i386",/' /var/lib/ubuntu-advantage/private/machine-access-esm-infra.json
EOF


lxc launch ubuntu-daily:trusty esm-sru-1a -c user.user-data="$(cat update-uat-trusty.yaml)"

echo "Wait for cloud-init to finish startup on trusty"
RUNLEVEL="NOTSET"
while ! [ "N 2" = "$RUNLEVEL" ]; do echo -n '.'; sleep 1; RUNLEVEL=`lxc exec esm-sru-1a runlevel`; done; echo

echo "Confirm u-a-t is already installed"
lxc exec esm-sru-1a -- apt-cache policy ubuntu-advantage-tools

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

# emit script to upgrade u-a-t
cat > add_uat_apt_pocket.sh << EOF
#/bin/bash
pocket_name=\$1
if [ "\$pocket_name" = "devel" ]; then
  echo deb [trusted=yes] http://ppa.launchpad.net/ci-train-ppa-service/3830/ubuntu trusty main | tee /etc/apt/sources.list.d/\$pocket_name.list
  apt-key add /ppa-key
else
  echo deb $ARCHIVE_URL \$pocket_name main | tee /etc/apt/sources.list.d/\$pocket_name.list
fi
EOF

lxc file push ppa-key esm-sru-1a/
lxc file push add_uat_apt_pocket.sh esm-sru-1a/
lxc file push fake_contract_delta.sh esm-sru-1a/
lxc exec esm-sru-1a chmod 755 /add_uat_apt_pocket.sh
lxc exec esm-sru-1a chmod 755 /fake_contract_delta.sh

echo "Enable esm via ubuntu-advantage enable-esm"
lxc exec esm-sru-1a -- ubuntu-advantage attach $UA_CONTRACT_TOKEN

echo "Confirm python-jinja2 is available for esm PPA"
lxc exec esm-sru-1a apt-cache policy python-jinja2

echo -- BEGIN test 1a: Confirm upgraded attached machine remains attached and esm enabled
echo "Upgrade u-a-t to trusty-proposed"
lxc exec esm-sru-1a /add_uat_apt_pocket.sh trusty-proposed #   or devel
lxc exec esm-sru-1a -- apt-get update -q;
lxc exec esm-sru-1a -- apt-get install -qy ubuntu-advantage-tools;

echo "Confirm python-jinja2 is available for esm PPA"
lxc exec esm-sru-1a apt-cache policy python-jinja2

lxc exec esm-sru-1a apt-get install python-jinja2

echo -- BEGIN test 1c: Confirm ua-contract architecture deltas don't unattach/disable esm on supported platforms
lxc exec esm-sru-1a /echo -- BEGIN test 1c: Confirm ua-contract architecture deltas do not unattach/disable esm on supported platforms
lxc exec esm-sru-1a /fake_contract_delta.sh
lxc exec esm-sru-1a ua refresh
lxc exec esm-sru-1a ua status

```
