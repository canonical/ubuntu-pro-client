#!/bin/bash
set -e

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
