pipeline {
    agent any

    environment {
        VM_NAME = "gitubuntu-ci-${currentBuild.getNumber()}"
        UACLIENT_BEHAVE_CONTRACT_TOKEN = credentials('ua-contract-token')
    }

    stages {
        stage ('Setup Dependencies') {
            steps {
                deleteDir()
                checkout scm
            }
        }
        stage ('Unit Tests') {
            steps {
                sh '''
                /usr/bin/tox -e py3
                '''
            }
        }
        stage ('Integration Tests') {
            steps {
                sh '''
                set +x
                /usr/bin/tox -e behave-vm-18.04
                '''
            }
        }
    }
    post {
        always {
            junit "pytest_results.xml"
        }
    }
}
