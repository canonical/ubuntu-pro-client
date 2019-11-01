# Test case 5: Start with minimal precise vm with enable-esm and dist-upgrade to trusty -poposed

5.
 a. Start with a fresh Ubuntu *precise* instance which does have u-a-t installed and esm enabled. Dist-upgrade to trusty, then upgrade to u-a-t from -proposed.
 b. In an identical instance, dist-upgrade to trusty with -proposed enabled.
 c. Confirm that the on-disk results of a) and b) are identical.

## 5a. Start with a fresh Ubuntu *precise* instance which does have u-a-t installed and esm enabled. Dist-upgrade to trusty, then upgrade to u-a-t from -proposed.

```
# Originally from https://gist.github.com/panlinux/e5bda289401660d77ed5eff4d980c30c  10/25
echo --- BEGIN test 5a: dist-upgrade an esm-enable precise-updates to trusty-updates, then upgrade to -proposed

mkdir -p 5a/var/lib/
echo "Launch precise container with allowing ssh access for <LP_ID>"

cat >precise.yaml <<EOF
#cloud-config
ssh_import_id: [<LP_ID>]
EOF
lxc launch ubuntu-daily:precise sru-precise -c user.user-data="$(cat precise.yaml)"

echo "Enable esm on precise"
lxc exec sru-precise ubuntu-advantage enable-esm <legacyToken>

echo "Dist-upgrade precise -> trusty"
VM_IP=`lxc list dev-p -c 4 | awk '/10/{print $2}'`
ssh ubuntu@$VM_IP
sudo mkdir -p /etc/update-manager/release-upgrades.d
echo -e "[Sources]\nAllowThirdParty=yes" > allow.cfg
sudo mv allow.cfg /etc/update-manager/release-upgrades.d
sudo do-release-upgrade # respond yes to any interactive prompts

echo "Confirm ansible is available for trusty esm PPA"
apt-cache policy ansible

echo "Upgrade u-a-t to trusty-proposed"
lxc file push ua_tools_install_from_pocket.sh sru-precise/
lxc exec sru-precise "bash /ua_tools_install_from_pocket.sh trusty-proposed"

lxc exec sru-precise -- dpkg -l > 5a/dpkg.list
lxc file pull -r sru-precise/etc 5a/
lxc file pull -r sru-precise/var/lib/ubuntu-advantage 5a/var/lib
lxc stop sru-precise
lxc delete sru-precise
```

##  b. In an identical instance, dist-upgrade to trusty with -proposed enabled.
```
echo --- BEGIN test 5b: dist-upgrade an esm-enable precise-proposed to trusty-proposed
mkdir -p 5b/var/lib/
echo "Launch precise container with allowing ssh access for <LP_ID>"

cat >precise.yaml <<EOF
#cloud-config
ssh_import_id: [<LP_ID>]
EOF
lxc launch ubuntu-daily:precise sru-precise -c user.user-data="$(cat precise.yaml)"

echo "Enable esm on precise"
lxc exec sru-precise ubuntu-advantage enable-esm <legacyToken>

echo "Upgrade u-a-t to precise-proposed" # no-op
lxc file push ua_tools_install_from_pocket.sh sru-precise/
lxc exec sru-precise "bash /ua_tools_install_from_pocket.sh sru-proposed"
lxc exec sru-precise "apt-get dist-upgrade"

echo "Dist-upgrade precise-proposed -> trusty-proposed"
VM_IP=`lxc list dev-p -c 4 | awk '/10/{print $2}'`
ssh ubuntu@$VM_IP
sudo mkdir -p /etc/update-manager/release-upgrades.d
echo -e "[Sources]\nAllowThirdParty=yes" > allow.cfg
sudo mv allow.cfg /etc/update-manager/release-upgrades.d
sudo do-release-upgrade # respond yes to any interactive prompts

echo "Confirm ansible is available for trusty esm PPA"
apt-cache policy ansible

lxc exec sru-precise -- dpkg -l > 5b/dpkg.list
lxc file pull -r sru-precise/etc 5b/
lxc file pull -r sru-precise/var/lib/ubuntu-advantage 5b/var/lib
lxc stop sru-precise
lxc delete sru-precise
```

##  c. Confirm that the on-disk results of a) and b) are identical.
```
echo --- BEGIN test 5c: confirm filesytem changes of test 5a and 5b are identical
dirr -urN 5a 5b
```
