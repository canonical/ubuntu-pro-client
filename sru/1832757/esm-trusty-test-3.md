# Test case 3: Install u-a-t on minimal system test enable-esm vs ua attach

3.
 a. Start with a fresh Ubuntu instance which does not have u-a-t installed (i.e. ubuntu-minimal is not installed). Install u-a-t from -updates. Enable esm with 'ubuntu-advantage enable-esm'. Upgrade to u-a-t from -proposed.
 b. In an identical instance, install u-a-t from -proposed. Enable esm with 'ubuntu-advantage attach'.
 c. Confirm that the on-disk results of a) and b) are identical.

```
# originally from https://gist.github.com/panlinux/4843bfc1e726a3f006aa44190411d582

sudo su -
# adjust if needed, i.e., point to a mirror
export ARCHIVE_URL=http://br.archive.ubuntu.com/ubuntu
export PROPOSED_REPO="deb $ARCHIVE_URL trusty-proposed main"

# these are needed
export LEGACY_ESM_TOKEN="user:password"
export UA_CONTRACT_TOKEN="<token>"

mkdir /esm-sru
cd /esm-sru
truncate -s 10G file.img
zpool create -O sync=disabled tank $(pwd)/file.img
zfs create tank/trusty-minimal
debootstrap --exclude=ubuntu-minimal trusty /tank/trusty-minimal $ARCHIVE_URL
zfs snapshot tank/trusty-minimal@fresh
# confirm no ubuntu-minimal nor ubuntu-advantage-tools
chroot /tank/trusty-minimal dpkg -l | grep -E "(ubuntu-minimal|ubuntu-advantage)"

# create a clone from trusty-minimal called trusty-3a
zfs clone tank/trusty-minimal@fresh tank/trusty-3a

# add extra pockets
cat >> /tank/trusty-3a/etc/apt/sources.list <<EOF
deb $ARCHIVE_URL trusty-updates main
deb $ARCHIVE_URL trusty-security main
EOF

# install u-a-t from updates
chroot /tank/trusty-3a/ apt-get update
chroot /tank/trusty-3a/ apt-get install ubuntu-advantage-tools -y

# enable esm
chroot /tank/trusty-3a/ ubuntu-advantage enable-esm "$LEGACY_ESM_TOKEN"

# upgrade to u-a-t from proposed
cat > /tank/trusty-3a/etc/apt/sources.list.d/proposed.list <<EOF
$PROPOSED_REPO
EOF
chroot /tank/trusty-3a/ apt-get update
chroot /tank/trusty-3a/ apt-get install ubuntu-advantage-tools -y

# clone the first fresh snapshot and call it trusyt-3b
zfs clone tank/trusty-minimal@fresh tank/trusty-3b

# install u-a-t directly from proposed
cat >> /tank/trusty-3b/etc/apt/sources.list <<EOF
deb $ARCHIVE_URL trusty-updates main
deb $ARCHIVE_URL trusty-security main
EOF

cat > /tank/trusty-3b/etc/apt/sources.list.d/proposed.list <<EOF
$PROPOSED_REPO
EOF

chroot /tank/trusty-3b/ apt-get update
chroot /tank/trusty-3b/ apt-get install ubuntu-advantage-tools -y

# with the new u-a-t from proposed, run attach, which also enables esm
chroot /tank/trusty-3b/ ua attach $UA_CONTRACT_TOKEN

# get files from both datasets, stripping the zfs prefix
find /tank/trusty-3a/ | sed -r 's,^/tank/[^/]+,,' | sort > trusty-3a.list
find /tank/trusty-3b/ | sed -r 's,^/tank/[^/]+,,' | sort > trusty-3b.list

# compare and verify the result
diff -u trusty-3a.list trusty-3b.list
--- trusty-3a.list	2019-10-24 11:20:19.207260287 -0300
+++ trusty-3b.list	2019-10-24 11:20:21.939243951 -0300
@@ -13723,7 +13723,6 @@
 /var/cache/apt/archives/sysv-rc_2.88dsf-41ubuntu6_all.deb
 /var/cache/apt/archives/tar_1.27.1-1_amd64.deb
 /var/cache/apt/archives/tzdata_2014b-1_all.deb
-/var/cache/apt/archives/ubuntu-advantage-tools_10ubuntu0.14.04.4_all.deb
 /var/cache/apt/archives/ubuntu-advantage-tools_19.6~ubuntu14.04.1~ppa2_amd64.deb
 /var/cache/apt/archives/ubuntu-keyring_2012.05.19_all.deb
 /var/cache/apt/archives/ucf_3.0027+nmu1_all.deb
@@ -13762,10 +13761,10 @@
 /var/lib/apt/lists/br.archive.ubuntu.com_ubuntu_dists_trusty-updates_InRelease
 /var/lib/apt/lists/br.archive.ubuntu.com_ubuntu_dists_trusty-updates_main_binary-amd64_Packages
 /var/lib/apt/lists/br.archive.ubuntu.com_ubuntu_dists_trusty-updates_main_i18n_Translation-en
-/var/lib/apt/lists/esm.ubuntu.com_ubuntu_dists_trusty-security_InRelease
-/var/lib/apt/lists/esm.ubuntu.com_ubuntu_dists_trusty-security_main_binary-amd64_Packages
-/var/lib/apt/lists/esm.ubuntu.com_ubuntu_dists_trusty-updates_InRelease
-/var/lib/apt/lists/esm.ubuntu.com_ubuntu_dists_trusty-updates_main_binary-amd64_Packages
+/var/lib/apt/lists/esm.ubuntu.com_ubuntu_dists_trusty-infra-security_InRelease
+/var/lib/apt/lists/esm.ubuntu.com_ubuntu_dists_trusty-infra-security_main_binary-amd64_Packages
+/var/lib/apt/lists/esm.ubuntu.com_ubuntu_dists_trusty-infra-updates_InRelease
+/var/lib/apt/lists/esm.ubuntu.com_ubuntu_dists_trusty-infra-updates_main_binary-amd64_Packages
 /var/lib/apt/lists/lock
 /var/lib/apt/lists/partial
 /var/lib/apt/lists/ppa.launchpad.net_ci-train-ppa-service_3830_ubuntu_dists_trusty_InRelease
@@ -14881,6 +14880,16 @@
 /var/lib/systemd/deb-systemd-helper-enabled/rsyslog.service.dsh-also
 /var/lib/systemd/deb-systemd-helper-enabled/syslog.service
 /var/lib/ubuntu-advantage
+/var/lib/ubuntu-advantage/machine-id
+/var/lib/ubuntu-advantage/private
+/var/lib/ubuntu-advantage/private/machine-access-cc-eal.json
+/var/lib/ubuntu-advantage/private/machine-access-esm-infra.json
+/var/lib/ubuntu-advantage/private/machine-access-fips.json
+/var/lib/ubuntu-advantage/private/machine-access-fips-updates.json
+/var/lib/ubuntu-advantage/private/machine-access-livepatch.json
+/var/lib/ubuntu-advantage/private/machine-access-support.json
+/var/lib/ubuntu-advantage/private/machine-token.json
+/var/lib/ubuntu-advantage/status.json
 /var/lib/ucf
 /var/lib/ucf/cache
 /var/lib/ucf/cache/:etc:rsyslog.d:50-default.conf

# since 3a just upgraded to new u-a-t but didn't run attach, it won't have the /var/lib/ubuntu-advantage contents that 3b has
# 3a also won't have the new "infra" name in its repositories, so that's another expected difference
# finally, 3b won't have the package from trusty-updates, since it got the proposed one installed directly

# diff the contents of /etc/apt. The expected changes are:
# - /etc/apt/auth.conf.d/90ubuntu-advantage: switch from old credentials to bearer token
# - /etc/apt/sources.list.d/ubuntu-esm-infra-trusty.list: switch to the infra repositories
diff -uNr /tank/trusty-3{a,b}/etc/apt


# OPTIONAL
# to go back to a clean state, without having to debootstrap again:
zfs destroy tank/trusty-3a
zfs destroy tank/trusty-3b
zfs rollback tank/trusty-minimal@fresh

# confirming
zfs list -t all -r tank
```
