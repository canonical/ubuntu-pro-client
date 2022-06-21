# Test case 2

2.
 a. Start with a fresh Ubuntu instance which does not have u-a-t installed (i.e. ubuntu-minimal is not installed). Install u-a-t from -updates.
 Do not enable ua. Upgrade to u-a-t from -proposed.
 b. In an identical instance, install u-a-t from -proposed.
 c. Confirm that the on-disk results of a) and b) are identical.

```
originally from https://gist.githubusercontent.com/panlinux/4caaf069356da7436d97b47afce32234/raw/d07504309557e9176ae887b8606b4de80c422e02/esm-trusty-test-2.txt


sudo su -
# adjust if needed, i.e., point to a mirror
export ARCHIVE_URL=http://br.archive.ubuntu.com/ubuntu
export PROPOSED_REPO="deb $ARCHIVE_URL trusty-proposed main"

mkdir /esm-sru
cd /esm-sru
truncate -s 10G file.img
zpool create -O sync=disabled tank $(pwd)/file.img
zfs create tank/trusty-minimal
debootstrap --exclude=ubuntu-minimal trusty /tank/trusty-minimal $ARCHIVE_URL
zfs snapshot tank/trusty-minimal@fresh
# confirm no ubuntu-minimal nor ubuntu-advantage-tools
chroot /tank/trusty-minimal dpkg -l | grep -E "(ubuntu-minimal|ubuntu-advantage)"

# create a clone from trusty-minimal called trusty-2a
zfs clone tank/trusty-minimal@fresh tank/trusty-2a

# add extra pockets
cat >> /tank/trusty-2a/etc/apt/sources.list <<EOF
deb $ARCHIVE_URL trusty-updates main
deb $ARCHIVE_URL trusty-security main
EOF

# install u-a-t from updates
chroot /tank/trusty-2a/ apt-get update
chroot /tank/trusty-2a/ apt-get install ubuntu-advantage-tools -y

# upgrade to u-a-t from proposed
cat > /tank/trusty-2a/etc/apt/sources.list.d/proposed.list <<EOF
$PROPOSED_REPO
EOF
chroot /tank/trusty-2a/ apt-get update
chroot /tank/trusty-2a/ apt-get install ubuntu-advantage-tools -y

# clone the first fresh snapshot and call it trusty-2b
zfs clone tank/trusty-minimal@fresh tank/trusty-2b

# install u-a-t directly from proposed
cat >> /tank/trusty-2b/etc/apt/sources.list <<EOF
deb $ARCHIVE_URL trusty-updates main
deb $ARCHIVE_URL trusty-security main
EOF

cat > /tank/trusty-2b/etc/apt/sources.list.d/proposed.list <<EOF
$PROPOSED_REPO
EOF

chroot /tank/trusty-2b/ apt-get update
chroot /tank/trusty-2b/ apt-get install ubuntu-advantage-tools -y

# get files from both datasets, stripping the zfs prefix
find /tank/trusty-2a/ | sed -r 's,^/tank/[^/]+,,' | sort > trusty-2a.list
find /tank/trusty-2b/ | sed -r 's,^/tank/[^/]+,,' | sort > trusty-2b.list

# compare and verify the result. The difference should be just that the 2a list has the intermediary u-a-t package from trusty-updates in the apt cache
diff -u trusty-2a.list trusty-2b.list
--- trusty-2a.list	2019-10-24 15:55:01.120848221 -0300
+++ trusty-2b.list	2019-10-24 15:55:01.256846583 -0300
@@ -13723,7 +13723,6 @@
 /var/cache/apt/archives/sysv-rc_2.88dsf-41ubuntu6_all.deb
 /var/cache/apt/archives/tar_1.27.1-1_amd64.deb
 /var/cache/apt/archives/tzdata_2014b-1_all.deb
-/var/cache/apt/archives/ubuntu-advantage-tools_10ubuntu0.14.04.4_all.deb
 /var/cache/apt/archives/ubuntu-advantage-tools_19.6~ubuntu14.04.1~ppa2_amd64.deb
 /var/cache/apt/archives/ubuntu-keyring_2012.05.19_all.deb
 /var/cache/apt/archives/ucf_3.0027+nmu1_all.deb


# diff the contents of /etc/apt, should be empty
diff -uNr /tank/trusty-2{a,b}/etc/apt

# OPTIONAL
# to go back to a clean state, without having to debootstrap again:
zfs destroy tank/trusty-2a
zfs destroy tank/trusty-2b
zfs rollback tank/trusty-minimal@fresh

# confirming
zfs list -t all -r tank
```
