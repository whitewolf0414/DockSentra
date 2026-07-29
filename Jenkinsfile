// ─────────────────────────────────────────────────────────────────────────────
// Jenkinsfile — dockerfile-security-checker
//
// Declarative pipeline with 6 stages:
//   1. Checkout
//   2. Build       — pip install
//   3. Test        — pytest
//   4. Security Scan — run our own CLI (gates on exit code)
//   5. Container Scan — docker build + Trivy (gates on CVE severity)
//   6. Archive      — publish reports/ as Jenkins build artifact
//
// The pipeline FAILS if:
//   - pytest fails
//   - CLI exit code == 1 (score < threshold OR critical failure)
//   - Trivy finds CRITICAL or HIGH CVEs in the container image
// ─────────────────────────────────────────────────────────────────────────────

pipeline {
    agent any

    environment {
        IMAGE_NAME  = "dockerfile-security-checker"
        IMAGE_TAG   = "${env.BUILD_NUMBER}"
        REPORT_DIR  = "reports"
        FAIL_UNDER  = "70"
    }

    options {
        timeout(time: 30, unit: 'MINUTES')
        buildDiscarder(logRotator(numToKeepStr: '10'))
        disableConcurrentBuilds()
    }

    stages {

        // ── Stage 1: Checkout ────────────────────────────────────────────────
        stage('Checkout') {
            steps {
                checkout scm
                echo "✔ Source checked out at commit ${env.GIT_COMMIT?.take(8)}"
            }
        }

        // ── Stage 2: Build ───────────────────────────────────────────────────
        stage('Build') {
            steps {
                sh '''
                bash <<'EOF'
                   set -e
                   set -o pipefail

                   python3 -m venv .venv
                   . .venv/bin/activate

                   python3 -m pip install --upgrade pip --quiet
                   python3 -m pip install -r requirements.txt --quiet

                   echo "✔ Dependencies installed"
EOF
                '''
            }
        }

        // ── Stage 3: Test ────────────────────────────────────────────────────
        stage('Test') {
            steps {
                sh '''
                bash <<'EOF'
                    set -e
                    set -o pipefail
                    . .venv/bin/activate
                    mkdir -p reports
                    python3 -m pytest tests/ \
                        -v \
                        --tb=short \
                        --junitxml=reports/pytest-results.xml \
                        2>&1 | tee reports/pytest-output.txt
EOF
                '''
            }
            post {
                always {
                    junit 'reports/pytest-results.xml'
                }
            }
        }

        // ── Stage 4: Security Scan ──────────────────────────────────────────
        // Run the CLI against:
        //   a) the deliberately bad sample (expected to fail — verify tool works)
        //   b) the project's own root Dockerfile (expected to pass — dogfooding)
        stage('Security Scan') {
            steps {
                sh '''
                bash <<'EOF'
                    set -e
                    set -o pipefail
                    . .venv/bin/activate
                    mkdir -p reports

                    echo "──────────────────────────────────────────"
                    echo " Scanning Dockerfile.bad (expect FAIL)"
                    echo "──────────────────────────────────────────"
                    python3 -m app.cli.cli \
                        --file app/sample/Dockerfile.bad \
                        --json \
                        --fail-under ${FAIL_UNDER} \
                        > reports/scan-bad.json || true
                    # We capture the JSON for archiving but do NOT gate on
                    # Dockerfile.bad failing — it's supposed to be insecure.

                    echo "──────────────────────────────────────────"
                    echo " Scanning project root Dockerfile (dogfood)"
                    echo "──────────────────────────────────────────"
                    python3 -m app.cli.cli \
                        --file Dockerfile \
                        --json \
                        --fail-under ${FAIL_UNDER} \
                        > reports/scan-root.json
                    # Exit code 1 here means the project's own Dockerfile
                    # failed the security check — this WILL fail the build.

                    echo "✔ Security scan complete"
EOF
                '''
            }
        }

        // ── Stage 5: Container Scan (Trivy) ─────────────────────────────────
        stage('Container Scan') {
            steps {
                sh '''
                bash <<'EOF'
                    set -e
                    set -o pipefail
                    docker build -t ${IMAGE_NAME}:${IMAGE_TAG} .

                    echo "──────────────────────────────────────────"
                    echo " Running Trivy vulnerability scan"
                    echo "──────────────────────────────────────────"
                    trivy image \
                        --exit-code 1 \
                        --severity CRITICAL,HIGH \
                        --ignorefile .trivyignore.yaml \
                        --no-progress \
                        --format json \
                        --output reports/trivy-report.json \
                        ${IMAGE_NAME}:${IMAGE_TAG}

                    # Also write a human-readable table for the log
                    trivy image \
                        --exit-code 0 \
                        --ignorefile .trivyignore.yaml \
                        --no-progress \
                        ${IMAGE_NAME}:${IMAGE_TAG}

                    echo "✔ Trivy scan passed (no unacknowledged CRITICAL/HIGH CVEs)"
EOF
                '''
            }
        }

        // ── Stage 6: Archive Reports ─────────────────────────────────────────
        // Actual archiving now happens in the top-level post{always{}} block
        // below, so reports survive even if an earlier stage (e.g. Container
        // Scan / Trivy) fails and this stage gets skipped.
        stage('Archive Reports') {
            steps {
                echo "Archiving security reports..."
            }
        }
    }

    // ── Post-pipeline hooks ────────────────────────────────────────────────
    post {
        success {
            echo """
╔══════════════════════════════════════════╗
║  ✅  PIPELINE PASSED                     ║
║  All security checks and tests passed.   ║
╚══════════════════════════════════════════╝
"""
        }
        failure {
            echo """
╔══════════════════════════════════════════╗
║  ❌  PIPELINE FAILED                     ║
║  Check the Security Scan or Test stage.  ║
╚══════════════════════════════════════════╝
"""
        }
        always {
            // Archive reports FIRST, before cleanWs() wipes the workspace.
            // allowEmptyArchive keeps this safe even if a stage failed
            // before generating every expected report file.
            archiveArtifacts(
                artifacts: 'reports/**',
                allowEmptyArchive: true,
                fingerprint: true
            )
            echo "✔ Reports archived to Jenkins build artifacts"

            // Clean up the built image to avoid disk pressure
            sh 'docker rmi ${IMAGE_NAME}:${IMAGE_TAG} || true'
            cleanWs()
        }
    }
}