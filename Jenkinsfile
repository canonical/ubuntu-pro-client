pipeline {
    agent any

    environment {
        VM_NAME = "gitubuntu-ci-${currentBuild.getNumber()}"
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
    }

    stages {
        stage ('Setup Dependencies') {
            steps {
                deleteDir()
                checkout scm
            }
        }
        stage ('Lint and Style') {
            parallel {
                stage("flake8") {
                    steps {
                        sh '/usr/bin/tox -e flake8'
                    }
                }
                stage("style") {
                    steps {
                        sh '/usr/bin/tox -e black'
                    }
                }
                stage("mypy") {
                    steps {
                        sh '/usr/bin/tox -e mypy'
                    }
                }
            }
        }
        stage ('Unit Tests') {
            steps {
                sh '/usr/bin/tox -e py3'
            }
        }
        stage ('Integration Tests') {
            parallel {
                stage("lxc 20.04") {
                    steps {
                        sh '''
                        set +x
                        /usr/bin/tox -e behave-vm-20.04
                        '''
                    }
                }
                stage("azuregeneric 16.04") {
                    steps {
                        sh '''
                        set +x
                        /usr/bin/tox -e behave-azuregeneric-16.04
                        '''
                    }
                }
                stage("awsgeneric 18.04") {
                    steps {
                        sh '''
                        set +x
                        /usr/bin/tox -e behave-awsgeneric-18.04
                        '''
                    }
                }
            }
        }
    }
}
