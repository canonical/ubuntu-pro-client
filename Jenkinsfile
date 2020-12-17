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
        stage ('Lint and Style') {
            parallel {
                stage("flake8") {
                    steps {
                        sh 'tox -e flake8'
                    }
                }
                stage("style") {
                    steps {
                        sh 'tox -e black'
                    }
                }
            }
        }
        stage ('Unit Tests') {
            steps {
                sh 'tox -e py3'
            }
        }
        stage ('Integration Tests') {
            steps {
               sh 'tox -e behave-vm-18.04'
            }
        }
    }
}
