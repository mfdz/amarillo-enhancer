pipeline {
    agent any
    environment {
        GITEA_CREDS = credentials('AMARILLO-JENKINS-GITEA-USER')
        PYPI_CREDS = credentials('AMARILLO-JENKINS-PYPI-USER')
        TWINE_REPO_URL = "https://git.gerhardt.io/api/packages/amarillo/pypi"
        DOCKER_REGISTRY_URL = 'https://git.gerhardt.io'
        OWNER = 'amarillo'
        IMAGE_NAME = 'amarillo-enhancer'
        DISTRIBUTION = '0.2'
        TAG = "${DISTRIBUTION}.${BUILD_NUMBER}"
    }
    stages {
        stage('Create virtual environment') {
            steps {
                echo 'Creating virtual environment'
                sh '''python3 -m venv .venv
                . .venv/bin/activate'''
            }
        }
        stage('Installing requirements') {
            steps {
                echo 'Installing packages'
                sh 'python3 -m pip install -r requirements.txt'
                sh 'python3 -m pip install --upgrade build'
                sh 'python3 -m pip install --upgrade twine'
            }
        }
        stage('Build') {
            steps {
                echo 'Cleaning up dist directory'
                dir("dist") {
                    deleteDir()
                }
                echo 'Building package'
                sh 'python3 -m build'
            }
        }
        stage('Publish package to GI') {
            steps {
                sh 'python3 -m twine upload --skip-existing --verbose --repository-url $TWINE_REPO_URL --username $GITEA_CREDS_USR --password $GITEA_CREDS_PSW ./dist/*'              
            }
        }
        stage('Publish package to PyPI') {
            when {
                branch 'main'
            }
            steps {
                sh 'python3 -m twine upload --verbose --username $PYPI_CREDS_USR --password $PYPI_CREDS_PSW ./dist/*'              
            }
        }
        stage('Build docker image') {
            when {
                anyOf { branch 'main'; branch 'dev' }
            }
            steps {
                echo 'Building image'
                script {
                    docker.build("${OWNER}/${IMAGE_NAME}:${TAG}")
                }
            }
        }
        stage('Push image to container registry') {
            when {
                anyOf { branch 'main'; branch 'dev' }
            }
            steps {
                echo 'Pushing image to registry'
                script {
                    docker.withRegistry(DOCKER_REGISTRY_URL, 'AMARILLO-JENKINS-GITEA-USER'){
                        def image = docker.image("${OWNER}/${IMAGE_NAME}:${TAG}")
                        image.push()
                        image.push('latest')
                    }
                }
            }
        }
    }
}