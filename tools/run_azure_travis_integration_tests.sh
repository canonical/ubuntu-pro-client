#!/bin/bash
source tools/base_travis_integration_tests.sh

install_pycloudlib() {
    git clone https://github.com/canonical/pycloudlib.git
    cd pycloudlib
    pip install -r requirements.txt
    cd ..
}

copy_deb_packages

if [ "$TRAVIS_EVENT_TYPE" = "cron" ] && [ "$TRAVIS_BRANCH" = "master" ]; then
  BUILD_PR=0
else
  create_pr_tar_file
fi

UACLIENT_BEHAVE_BUILD_PR=${BUILD_PR} make test

install_pycloudlib
echo $TRAVIS_JOB_NUMBER
python3 server-test-scripts/ubuntu-advantage-client/azure_cleanup.py --suffix-tag ${TRAVIS_JOB_NUMBER/./-} --client-id ${UACLIENT_BEHAVE_AZ_CLIENT_ID} --client-secret ${UACLIENT_BEHAVE_AZ_CLIENT_SECRET} --subscription-id ${UACLIENT_BEHAVE_AZ_SUBSCRIPTION_ID} --tenant-id ${UACLIENT_BEHAVE_AZ_TENANT_ID} || true
