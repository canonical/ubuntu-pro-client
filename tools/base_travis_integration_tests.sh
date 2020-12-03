#!/bin/bash
set -e

UA_STAGING_PPA=ppa:ua-client/staging
UA_STAGING_PPA_KEYID=6E34E7116C0BC933

remove_lxd() {
  sudo apt-get remove --yes --purge lxd lxd-client
  sudo rm -Rf /var/lib/lxd
}

copy_deb_packages() {
  mkdir deb-artifacts
  cp *-debs/* deb-artifacts
}

create_pr_tar_file() {
  cd $TRAVIS_BUILD_DIR/..
  tar -zcf pr_source.tar.gz ubuntu-advantage-client
  cp pr_source.tar.gz /tmp
  ls -lh /tmp
  cd $TRAVIS_BUILD_DIR
}
