// CI/CD pipeline for the phishing-detection-analysis project.
// Jenkins job type: "Pipeline" -> "Pipeline script from SCM" (Git), script path "Jenkinsfile".
pipeline {
    agent any

    options {
        timestamps()
        disableConcurrentBuilds()
        buildDiscarder(logRotator(numToKeepStr: '10'))
        timeout(time: 20, unit: 'MINUTES')
    }

    // Checks the repository for new commits every ~2 minutes (works without a public webhook URL)
    triggers {
        pollSCM('H/2 * * * *')
    }

    parameters {
        string(name: 'IMAGE_NAME', defaultValue: 'phishing-detector',
               description: 'Image repository. For Docker Hub use <your-user>/phishing-detector')
        booleanParam(name: 'PUSH_IMAGE', defaultValue: false,
                     description: 'Push the image to Docker Hub (needs credentials "dockerhub-credentials")')
        booleanParam(name: 'DEPLOY_TEST', defaultValue: true,
                     description: 'Deploy the new image to the local test environment (CD)')
    }

    environment {
        IMAGE_TAG = "${env.BUILD_NUMBER}"
        TEST_CONTAINER = 'phishing-api-test'
    }

    stages {
        stage('Checkout') {
            steps {
                checkout scm
                sh 'git log -1 --pretty="Commit: %h  %s"'
            }
        }

        stage('Install dependencies') {
            steps {
                sh '''
                    python3 -m venv .venv
                    . .venv/bin/activate
                    pip install --quiet --upgrade pip
                    pip install --quiet -r requirements-dev.txt
                '''
            }
        }

        stage('Lint') {
            steps {
                sh '. .venv/bin/activate && ruff check .'
            }
        }

        stage('Unit tests') {
            steps {
                sh '''
                    . .venv/bin/activate
                    mkdir -p reports
                    pytest -q --junitxml=reports/junit.xml \
                           --cov=src --cov-report=xml:reports/coverage.xml --cov-fail-under=85
                '''
            }
            post {
                always {
                    junit allowEmptyResults: true, testResults: 'reports/junit.xml'
                    archiveArtifacts artifacts: 'reports/*.xml', allowEmptyArchive: true
                }
            }
        }

        stage('Build Docker image') {
            steps {
                sh '''
                    docker build -t "${IMAGE_NAME}:${IMAGE_TAG}" -t "${IMAGE_NAME}:latest" .
                    docker image ls "${IMAGE_NAME}"
                '''
            }
        }

        stage('Smoke-test image') {
            steps {
                // Runs the CLI inside the freshly built image
                sh 'docker run --rm "${IMAGE_NAME}:${IMAGE_TAG}" python -m src.cli evaluate'
            }
        }

        stage('Push to Docker Hub') {
            when { expression { params.PUSH_IMAGE } }
            steps {
                withCredentials([usernamePassword(credentialsId: 'dockerhub-credentials',
                                                  usernameVariable: 'DH_USER',
                                                  passwordVariable: 'DH_PASS')]) {
                    sh '''
                        echo "$DH_PASS" | docker login -u "$DH_USER" --password-stdin
                        docker push "${IMAGE_NAME}:${IMAGE_TAG}"
                        docker push "${IMAGE_NAME}:latest"
                        docker logout
                    '''
                }
            }
        }

        stage('Deploy to test environment') {
            when { expression { params.DEPLOY_TEST } }
            steps {
                sh '''
                    docker rm -f "${TEST_CONTAINER}" 2>/dev/null || true
                    docker run -d --name "${TEST_CONTAINER}" -p 8000:8000 "${IMAGE_NAME}:${IMAGE_TAG}"

                    # Wait until the API answers, then run a prediction request (post-deploy check)
                    for i in $(seq 1 20); do
                        if docker exec "${TEST_CONTAINER}" python -c \
                           "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=2)"; then
                            echo "API is up"; break
                        fi
                        sleep 2
                    done
                    docker exec "${TEST_CONTAINER}" python - <<'PY'
import json, urllib.request
req = urllib.request.Request(
    "http://127.0.0.1:8000/predict",
    data=json.dumps({"urls": ["http://paypal-login-verify.test/confirm", "https://github.com"]}).encode(),
    headers={"Content-Type": "application/json"})
result = json.load(urllib.request.urlopen(req, timeout=5))
print(result)
assert result[0]["label"] == 1 and result[1]["label"] == 0, "unexpected predictions"
print("Deployment check passed")
PY
                '''
            }
        }
    }

    post {
        success { echo "Build #${env.BUILD_NUMBER} succeeded: ${params.IMAGE_NAME}:${env.IMAGE_TAG}" }
        failure { echo 'Build failed - see the console output of the failed stage.' }
    }
}
