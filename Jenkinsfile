pipeline {
    agent any

    environment {
        VM_NAME = "gitubuntu-ci-${currentBuild.getNumber()}"
    }

    stages {
        stage ('Setup Dependencies') {
            steps {
                deleteDir()
                checkout scm
                sh 'python3 -m venv /tmp/flake8'
                sh '. /tmp/flake8/bin/activate'
                sh 'make testdeps'
            }
        }
        stage ('Unit Tests') {
            steps {
                sh '''
                python3 -V
                tox -e py3
                '''
            }
        }
        stage ('Integration Tests') {
            steps {
                withCredentials([usernameColonPassword(credentialsId: 'ua-contract-token', variable: 'UACLIENT_BEHAVE_CONTRACT_TOKEN')]) {
                    sh '''
                    set +x
                    tox -e behave-vm-18.04
                   '''
                }
            }
        }
    }
}
