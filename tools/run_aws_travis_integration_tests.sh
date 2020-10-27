#!/bin/bash
source tools/base_travis_integration_tests.sh

copy_deb_packages

if [ "$TRAVIS_EVENT_TYPE" = "cron" ] && ["$TRAVIS_BRANCH" = "master"]; then
  BUILD_PR=0
else
  create_pr_tar_file
fi

UACLIENT_BEHAVE_BUILD_PR=${BUILD_PR} make test

for key_name in `ls *pem`; do
    K=${key_name/ec2-/};
    python3 server-test-scripts/ubuntu-advantage-client/ec2_cleanup.py -t ${K%.pem} || true
done;
