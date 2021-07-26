pipeline {
    agent any

    environment {
        TMPDIR = "/tmp/$BUILD_TAG/"
        UACLIENT_BEHAVE_JENKINS_BUILD_TAG = "${BUILD_TAG}"
        UACLIENT_BEHAVE_JENKINS_CHANGE_ID = "${CHANGE_ID}"
        UACLIENT_BEHAVE_BUILD_PR=1
        UACLIENT_BEHAVE_CONTRACT_TOKEN = credentials('ua-contract-token')
        UACLIENT_BEHAVE_AWS_ACCESS_KEY_ID = credentials('ua-aws-access-key-id')
        UACLIENT_BEHAVE_AWS_SECRET_ACCESS_KEY = credentials(
            'ua-aws-secret-access-key'
        )
        UACLIENT_BEHAVE_AZ_CLIENT_ID = credentials('ua-azure-client-id')
        UACLIENT_BEHAVE_AZ_CLIENT_SECRET = credentials(
            'ua-azure-client-secret'
        )
        UACLIENT_BEHAVE_AZ_TENANT_ID = credentials('ua-azure-tenant')
        UACLIENT_BEHAVE_AZ_SUBSCRIPTION_ID = credentials(
            'ua-azure-subscription-id'
        )
        UACLIENT_BEHAVE_CONTRACT_TOKEN_STAGING = credentials(
            'ua-contract-token-staging'
        )
        UACLIENT_BEHAVE_CONTRACT_TOKEN_STAGING_EXPIRED = credentials(
            'ua-contract-token-staging-expired'
        )
        JOB_SUFFIX = sh(returnStdout: true, script: "basename ${JOB_NAME}| cut -d'-' -f2").trim()
    }

    stages {
        stage ('Setup Dependencies') {
            steps {
                deleteDir()
                checkout scm
                sh '''
                python3 -m venv $TMPDIR
                . $TMPDIR/bin/activate
                pip install tox  # for tox supporting --parallel--safe-build
                pip install tox-pip-version  # To freeze pip version on some tests
                '''
            }
        }
        stage("flake8") {
            steps {
                sh '''
                set +x
                tox -e flake8
                '''
            }
        }
        stage("style") {
            steps {
                sh '''
                set +x
                tox -e black
                '''
            }
        }
        stage("mypy") {
            steps {
                sh '''
                set +x
                tox -e mypy
                '''
            }
        }
        stage ('Unit Tests') {
            steps {
                sh '''
                set +x
                . $TMPDIR/bin/activate
                tox --parallel--safe-build -e py3
                tox --parallel--safe-build -e py3-xenial
                tox --parallel--safe-build -e py3-bionic
                '''
            }
        }
        stage ('Package builds') {
            parallel {
                stage ('Package build: 16.04') {
                    environment {
                        BUILD_SERIES = "xenial"
                        SERIES_VERSION = "16.04"
                        PKG_VERSION = sh(returnStdout: true, script: "dpkg-parsechangelog --show-field Version").trim()
                        NEW_PKG_VERSION = "${PKG_VERSION}~${SERIES_VERSION}~${JOB_SUFFIX}"
                        ARTIFACT_DIR = "${TMPDIR}${BUILD_SERIES}"
                    }
                    steps {
                        sh '''
                        set -x
                        mkdir ${ARTIFACT_DIR}
                        cp debian/changelog ${WORKSPACE}/debian/changelog-${SERIES_VERSION}
                        sed -i "s/${PKG_VERSION}/${NEW_PKG_VERSION}/" ${WORKSPACE}/debian/changelog-${SERIES_VERSION}
                        dpkg-source -l${WORKSPACE}/debian/changelog-${SERIES_VERSION} -b .
                        sbuild --resolve-alternatives --nolog --verbose --dist=${BUILD_SERIES} --no-run-lintian --append-to-version=~${SERIES_VERSION}  ../ubuntu-advantage-tools*${NEW_PKG_VERSION}*dsc
                        cp ./ubuntu-advantage-tools*${SERIES_VERSION}*.deb ${ARTIFACT_DIR}/ubuntu-advantage-tools-${BUILD_SERIES}.deb
                        cp ./ubuntu-advantage-pro*${SERIES_VERSION}*.deb ${ARTIFACT_DIR}/ubuntu-advantage-pro-${BUILD_SERIES}.deb
                        '''
                    }
                }
                stage ('Package build: 18.04') {
                    environment {
                        BUILD_SERIES = "bionic"
                        SERIES_VERSION = "18.04"
                        PKG_VERSION = sh(returnStdout: true, script: "dpkg-parsechangelog --show-field Version").trim()
                        NEW_PKG_VERSION = "${PKG_VERSION}~${SERIES_VERSION}~${JOB_SUFFIX}"
                        ARTIFACT_DIR = "${TMPDIR}${BUILD_SERIES}"
                    }
                    steps {
                        sh '''
                        set -x
                        mkdir ${ARTIFACT_DIR}
                        cp debian/changelog ${WORKSPACE}/debian/changelog-${SERIES_VERSION}
                        sed -i "s/${PKG_VERSION}/${NEW_PKG_VERSION}/" ${WORKSPACE}/debian/changelog-${SERIES_VERSION}
                        dpkg-source -l${WORKSPACE}/debian/changelog-${SERIES_VERSION} -b .
                        sbuild --resolve-alternatives --nolog --verbose --dist=${BUILD_SERIES} --no-run-lintian --append-to-version=~${SERIES_VERSION}  ../ubuntu-advantage-tools*${NEW_PKG_VERSION}*dsc
                        cp ./ubuntu-advantage-tools*${SERIES_VERSION}*.deb ${ARTIFACT_DIR}/ubuntu-advantage-tools-${BUILD_SERIES}.deb
                        cp ./ubuntu-advantage-pro*${SERIES_VERSION}*.deb ${ARTIFACT_DIR}/ubuntu-advantage-pro-${BUILD_SERIES}.deb
                        '''
                    }
                }
                stage ('Package build: 20.04') {
                    environment {
                        BUILD_SERIES = "focal"
                        SERIES_VERSION = "20.04"
                        PKG_VERSION = sh(returnStdout: true, script: "dpkg-parsechangelog --show-field Version").trim()
                        NEW_PKG_VERSION = "${PKG_VERSION}~${SERIES_VERSION}~${JOB_SUFFIX}"
                        ARTIFACT_DIR = "${TMPDIR}${BUILD_SERIES}"
                    }
                    steps {
                        sh '''
                        set -x
                        mkdir ${ARTIFACT_DIR}
                        cp debian/changelog ${WORKSPACE}/debian/changelog-${SERIES_VERSION}
                        sed -i "s/${PKG_VERSION}/${NEW_PKG_VERSION}/" ${WORKSPACE}/debian/changelog-${SERIES_VERSION}
                        dpkg-source -l${WORKSPACE}/debian/changelog-${SERIES_VERSION} -b .
                        sbuild --resolve-alternatives --nolog --verbose --dist=${BUILD_SERIES} --no-run-lintian --append-to-version=~${SERIES_VERSION}  ../ubuntu-advantage-tools*${NEW_PKG_VERSION}*dsc
                        cp ./ubuntu-advantage-tools*${SERIES_VERSION}*.deb ${ARTIFACT_DIR}/ubuntu-advantage-tools-${BUILD_SERIES}.deb
                        cp ./ubuntu-advantage-pro*${SERIES_VERSION}*.deb ${ARTIFACT_DIR}/ubuntu-advantage-pro-${BUILD_SERIES}.deb
                        '''
                    }
                }
            }
        }
        stage ('Integration Tests') {
            parallel {
                stage("lxc 16.04") {
                    environment {
                        UACLIENT_BEHAVE_DEBS_PATH = "${TMPDIR}xenial/"
                        UACLIENT_BEHAVE_ARTIFACT_DIR = "artifacts/behave-lxd-16.04"
                        UACLIENT_BEHAVE_EPHEMERAL_INSTANCE = 1
                        UACLIENT_BEHAVE_SNAPSHOT_STRATEGY = 1
                    }
                    steps {
                        sh '''
                        set +x
                        . $TMPDIR/bin/activate
                        tox --parallel--safe-build -e behave-lxd-16.04
                        '''
                    }
                }
                stage("lxc 18.04") {
                    environment {
                        UACLIENT_BEHAVE_DEBS_PATH = "${TMPDIR}bionic/"
                        UACLIENT_BEHAVE_ARTIFACT_DIR = "artifacts/behave-lxd-18.04"
                        UACLIENT_BEHAVE_EPHEMERAL_INSTANCE = 1
                        UACLIENT_BEHAVE_SNAPSHOT_STRATEGY = 1
                    }
                    steps {
                        sh '''
                        set +x
                        . $TMPDIR/bin/activate
                        tox --parallel--safe-build -e behave-lxd-18.04
                        '''
                    }
                }
                stage("lxc 20.04") {
                    environment {
                        UACLIENT_BEHAVE_DEBS_PATH = "${TMPDIR}focal/"
                        UACLIENT_BEHAVE_ARTIFACT_DIR = "artifacts/behave-lxd-20.04"
                        UACLIENT_BEHAVE_EPHEMERAL_INSTANCE = 1
                        UACLIENT_BEHAVE_SNAPSHOT_STRATEGY = 1
                    }
                    steps {
                        sh '''
                        set +x
                        . $TMPDIR/bin/activate
                        tox --parallel--safe-build -e behave-lxd-20.04
                        '''
                    }
                }
                stage("lxc vm 20.04") {
                    environment {
                        UACLIENT_BEHAVE_DEBS_PATH = "${TMPDIR}focal/"
                        UACLIENT_BEHAVE_ARTIFACT_DIR = "artifacts/behave-vm-20.04"
                        UACLIENT_BEHAVE_EPHEMERAL_INSTANCE = 1
                    }
                    steps {
                        sh '''
                        set +x
                        . $TMPDIR/bin/activate
                        tox --parallel--safe-build -e behave-vm-20.04
                        '''
                    }
                }
                stage("awspro 18.04") {
                    environment {
                        UACLIENT_BEHAVE_DEBS_PATH = "${TMPDIR}bionic/"
                        UACLIENT_BEHAVE_ARTIFACT_DIR = "artifacts/behave-awspro-18.04"
                    }
                    steps {
                        sh '''
                        set +x
                        . $TMPDIR/bin/activate
                        tox --parallel--safe-build -e behave-awspro-18.04
                        '''
                    }
                }
            }
        }
    }
    post {
        always {
            script {
                try {
                    sh '''
                    set +x
                    DATE=`date -d 'now+1day' +%m/%d/%Y`
                    git clone https://github.com/canonical/server-test-scripts.git
                    python3 server-test-scripts/ubuntu-advantage-client/lxd_cleanup.py --prefix ubuntu-behave-test-$CHANGE_ID --before-date $DATE || true
                    '''

                    junit "pytest_results.xml"
                    junit "reports/*.xml"
                } catch (Exception e) {
                    echo e.toString()
                    currentBuild.result = 'UNSTABLE'
                }
                try {
                    archiveArtifacts "artifacts/**/**/*"
                } catch (Exception e) {
                    echo "No integration test artifacts found. Presume success."
                }
            }
        }
    }
}
