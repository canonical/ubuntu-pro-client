#!/bin/bash
source tools/base_travis_integration_tests.sh

copy_deb_packages

if [ "$TRAVIS_EVENT_TYPE" = "cron" ]; then
  BUILD_PR=0
  if [ "$TRAVIS_BRANCH" != "${TRAVIS_BRANCH/release-}" ]; then
      # Run cron of release-XX branches against UA_STAGING_PPA
      export UACLIENT_BEHAVE_PPA=${UA_STAGING_PPA}
      export UACLIENT_BEHAVE_PPA_KEYID=${UA_STAGING_PPA_KEYID}
  fi
else
  create_pr_tar_file
fi

UACLIENT_BEHAVE_BUILD_PR=${BUILD_PR} make test

for key_name in `ls *pem`; do
    K=${key_name/ec2-/};
    python3 server-test-scripts/ubuntu-advantage-client/ec2_cleanup.py -t ${K%.pem} || true
done;
