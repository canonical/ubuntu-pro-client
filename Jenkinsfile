pipeline {
    agent any

    environment {
        TMPDIR = "/tmp/$BUILD_TAG/"
        UACLIENT_BEHAVE_JENKINS_BUILD_TAG = "${BUILD_TAG}"
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
                '''
            }
        }
        stage ('Lint and Style') {
            parallel {
                stage("flake8") {
                    steps {
                        sh '''
                        set +x
                        . $TMPDIR/bin/activate
                        tox --parallel--safe-build -e flake8
                        '''
                    }
                }
                stage("style") {
                    steps {
                        sh '''
                        set +x
                        . $TMPDIR/bin/activate
                        tox --parallel--safe-build -e black
                        '''
                    }
                }
                stage("mypy") {
                    steps {
                        sh '''
                        set +x
                        . $TMPDIR/bin/activate
                        tox --parallel--safe-build -e mypy
                        '''
                    }
                }
            }
        }
        stage ('Unit Tests') {
            steps {
                sh '''
                set +x
                . $TMPDIR/bin/activate
                tox --parallel--safe-build -e py3
                '''
            }
        }
        stage ('Integration Tests') {
            parallel {
                stage("lxc 14.04") {
                    environment {
                        UACLIENT_BEHAVE_DEBS_PATH = "${TMPDIR}trusty/"
                    }
                    steps {
                        sh '''
                        set +x
                        . $TMPDIR/bin/activate
                        tox --parallel--safe-build -e behave-lxd-14.04
                        '''
                    }
                }
                stage("lxc 16.04") {
                    environment {
                        UACLIENT_BEHAVE_DEBS_PATH = "${TMPDIR}xenial/"
                    }
                    steps {
                        sh '''
                        set +x
                        . $TMPDIR/bin/activate
                        tox --parallel--safe-build -e behave-16.04
                        '''
                    }
                }
                stage("lxc 18.04") {
                    environment {
                        UACLIENT_BEHAVE_DEBS_PATH = "${TMPDIR}bionic/"
                    }
                    steps {
                        sh '''
                        set +x
                        . $TMPDIR/bin/activate
                        tox --parallel--safe-build -e behave-lxd-18.04
                        '''
                    }
                }
                stage("lxc vm 20.04") {
                    environment {
                        UACLIENT_BEHAVE_DEBS_PATH = "${TMPDIR}focal/"
                    }
                    steps {
                        sh '''
                        set +x
                        . $TMPDIR/bin/activate
                        tox --parallel--safe-build -e behave-vm-20.04
                        '''
                    }
                }
                stage("azuregeneric 16.04") {
                    environment {
                        UACLIENT_BEHAVE_DEBS_PATH = "${TMPDIR}xenial/"
                    }
                    steps {
                        sh '''
                        set +x
                        . $TMPDIR/bin/activate
                        tox --parallel--safe-build -e behave-azuregeneric-16.04
                        '''
                    }
                }
                stage("awsgeneric 18.04") {
                    environment {
                        UACLIENT_BEHAVE_DEBS_PATH = "${TMPDIR}bionic/"
                    }
                    steps {
                        sh '''
                        set +x
                        . $TMPDIR/bin/activate
                        tox --parallel--safe-build -e behave-awsgeneric-18.04
                        '''
                    }
                }
            }
        }
    }
}
