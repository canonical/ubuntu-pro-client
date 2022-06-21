# Test case 4: Start from cloud-image with u-a-t installed, compar enable-esm vs ua attach

4.
 a. Start with a fresh Ubuntu instance which does have u-a-t installed. Enable esm with 'ubuntu-advantage enable-esm'. Upgrade to u-a-t from -proposed.
 b. In an identical instance, upgrade to u-a-t from -proposed. Enable esm with 'ubuntu-advantage attach'.
 c. Confirm that the on-disk results of a) and b) are identical other than legacyToken|contractToken

```
# Originally from https://gist.github.com/blackboxsw/0e968aeabd42c23df619d29c7906c76e

export LEGACY_ESM_TOKEN=<ppauser:password>
export UA_CONTRACT_TOKEN=<NewContractToken>
export ARCHIVE_URL=http://archive.ubuntu.com/ubuntu

echo -- BEGIN test 4a: enable esm via `ubuntu-advantage enable-esm` on typical trusty-updates cloud-images which already have -updates installed

# Launch a basic trusty cloud-image that is updated to latest ubuntu-advantage-tools from -updates
cat > update-uat-trusty.yaml <<EOF
#cloud-config
package_update: true
package_upgrade: true
runcmd:
 - apt-get install -qy ubuntu-advantage-tools 
EOF

lxc launch ubuntu-daily:trusty esm-sru-4a -c user.user-data="$(cat update-uat-trusty.yaml)"

echo "Wait for cloud-init to finish startup on trusty"
RUNLEVEL="NOTSET"
while ! [ "N 2" = "$RUNLEVEL" ]; do echo -n '.'; sleep 1; RUNLEVEL=`lxc exec esm-sru-4a runlevel`; done; echo
mkdir /esm-sru
cd /esm-sru
mkdir 4a 4b

echo "Confirm u-a-t is already installed"
lxc exec esm-sru-4a -- apt-cache policy ubuntu-advantage-tools

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

lxc file push ppa-key esm-sru-4a/
lxc file push add_uat_apt_pocket.sh esm-sru-4a/
lxc exec esm-sru-4a chmod 755 /add_uat_apt_pocket.sh

echo "Make a pristine lxc snapshot for 4a and 4b"
lxc snapshot esm-sru-4a esm-sru-4a-pristine

echo "Enable esm via ubuntu-advantage enable-esm"
lxc exec esm-sru-4a -- ubuntu-advantage enable-esm $LEGACY_ESM_TOKEN

echo "Confirm ansible is available for esm PPA"
lxc exec esm-sru-4a apt-cache policy ansible

echo "Upgrade u-a-t to trusty-proposed"
lxc exec esm-sru-4a /add_uat_apt_pocket.sh trusty-proposed #   or devel
lxc exec esm-sru-4a -- apt-get update -q;
lxc exec esm-sru-4a -- apt-get install -qy ubuntu-advantage-tools;

echo "Confirm ansible is available for esm PPA"
lxc exec esm-sru-4a apt-cache policy ansible

lxc exec esm-sru-4a -- find / -xdev | sort > 4a/files.list
lxc file pull -r esm-sru-4a/etc 4a/


echo -- BEGIN test 4b: upgrade u-a-t to -proposed version on typical trusty-updates cloud-images which already have -updates installed
lxc restore esm-sru-4a esm-sru-4a-pristine

echo "Confirm u-a-t is already installed from trusty-updates v. 10ubuntu0.14.04.4"
lxc exec esm-sru-4a -- apt-cache policy ubuntu-advantage-tools

echo "Upgrade u-a-t to trusty-proposed"
lxc exec esm-sru-4a /add_uat_apt_pocket.sh trusty-proposed   # or devel
lxc exec esm-sru-4a -- apt-get update -q;
lxc exec esm-sru-4a -- apt-get install -qy ubuntu-advantage-tools;

echo "Enable esm via: ua attach <contractToken>"
lxc exec esm-sru-4a ua attach $UA_CONTRACT_TOKEN

echo "Confirm ansible is available for esm PPA"
lxc exec esm-sru-4a apt-cache policy ansible

lxc exec esm-sru-4a -- find / -xdev | sort > 4b/files.list
lxc file pull -r esm-sru-4a/etc 4b/

echo --- BEGIN test 4c: ensure no filesystem diffs between 4a and 4b with exception of token used
diff -urN 4a 4b
```
