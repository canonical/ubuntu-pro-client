pipeline {
    agent any

    environment {
        VM_NAME = "gitubuntu-ci-${currentBuild.getNumber()}"
    }

    stages {
        stage ('Lint and Style') {
            steps {
                deleteDir()
                checkout scm
                python3 -m venv /tmp/flake8
                . /tmp/flake8/bin/activate
                make testdeps
                tox -e py3,flake8
            }
        }
        stage ('Unit Tests') {
            steps {
                echo "TESTS"
            }
        }
    }
}
