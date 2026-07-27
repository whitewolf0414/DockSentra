# Dockerfile Security Checker

## Project Overview

Dockerfile Security Checker is a hybrid DevSecOps application designed to identify common security misconfigurations in Dockerfiles before container images are built and deployed.

The application provides both a **Command Line Interface (CLI)** and a **Web Interface**, allowing developers to scan Dockerfiles manually, while also enabling automated security checks inside CI/CD pipelines.

The project follows a modular architecture where a single scanning engine is shared between the CLI and Web interface, making the application reusable, maintainable, and easy to extend.

---

# Project Objectives

- Detect insecure Dockerfile configurations.
- Improve container security before deployment.
- Automate Dockerfile security validation.
- Demonstrate DevSecOps pipeline integration.
- Generate security reports for developers.
- Learn modern DevOps and DevSecOps practices.

---

# Problem Statement

Many developers unintentionally create insecure Dockerfiles.

Common mistakes include:

- Running containers as the root user.
- Using the `latest` image tag.
- Missing `HEALTHCHECK`.
- Exposing unnecessary ports.
- Ignoring Docker security best practices.

These mistakes can introduce security risks into production environments. Dockerfile Security Checker helps identify these issues early during development.

---

# Related Domains

This project is related to:

- DevOps
- DevSecOps
- Cloud Security
- Container Security
- Infrastructure as Code (IaC)
- Secure Software Development
- Continuous Integration (CI)
- Continuous Delivery (CD)
- Static Configuration Analysis

---

# Technologies Used

## Programming

- Python

## CLI

- Typer
- Rich

## Web

- Flask
- HTML
- CSS
- JavaScript

## Containerization

- Docker

## CI/CD

- Jenkins

## Version Control

- Git
- GitHub

## Security

- Trivy

---

# DevSecOps Components

| Technology | Purpose |
|------------|---------|
| Git | Version Control |
| GitHub | Source Code Repository |
| Jenkins | Continuous Integration |
| Docker | Containerization |
| Trivy | Container Vulnerability Scanner |
| Python | Application Development |
| Flask | Web Interface |
| Typer | Command Line Interface |

---

# Project Architecture

```text
                            User
                              │
                ┌─────────────┴─────────────┐
                │                           │
                ▼                           ▼
         CLI Interface               Web Interface
                │                           │
                └─────────────┬─────────────┘
                              │
                      Scanning Engine
                              │
        ┌───────────────┬───────────────┬───────────────┐
        │               │               │               │
        ▼               ▼               ▼               ▼
   Dockerfile      Rule Engine     Score Engine    Report Generator
     Parser
                              │
                 ┌────────────┴────────────┐
                 │                         │
                 ▼                         ▼
         CLI Report                HTML / JSON Report
```

---

# Application Workflow

```text
Developer
    →
Write Dockerfile
    →
Run Dockerfile Security Checker
    →
Read Dockerfile
    →
Parse Instructions
    →
Execute Security Rules
    →
Calculate Security Score
    →
Generate Security Report
    →
Display Results (CLI / Web)
```

---

# DevSecOps Pipeline Workflow

```text
Developer
    →
Git
    →
GitHub Repository
    →
Jenkins Pipeline
    →
Checkout Source Code
    →
Install Dependencies
    →
Run Unit Tests
    →
Build Docker Image
    →
Trivy Vulnerability Scan
    →
Run Dockerfile Security Checker
    →
PASS / FAIL
    →
Deploy Application
```

---

# CLI Workflow

```text
User
    →
Open Terminal
    →
Run Scan Command
    →
Read Dockerfile
    →
Analyze Security Rules
    →
Calculate Score
    →
Generate Report
    →
Display Results
```

Example:

```bash
python -m app.cli.cli scan sample/Dockerfile.bad
```

---

# Web Workflow

```text
User
    →
Open Browser
    →
Upload Dockerfile
    →
Click Scan
    →
Read Dockerfile
    →
Analyze Security Rules
    →
Calculate Score
    →
Generate HTML Report
    →
Display Results
```

---

# Core Features

- Dockerfile security scanning
- CLI interface
- Web interface
- Shared scanning engine
- Security rule validation
- Risk score calculation
- JSON report generation
- HTML report generation
- Modular architecture
- Jenkins integration
- Docker support
- Trivy compatibility

---

# Security Rules

The scanner currently checks for:

- Running as root (`USER root`)
- Using `latest` image tags
- Missing `HEALTHCHECK`
- Exposed SSH port (`EXPOSE 22`)
- Multiple exposed ports
- Empty Dockerfiles

---

# Project Structure

```text
dockerfile-security-checker/
│
├── app/
│   ├── engine/
│   ├── cli/
│   ├── web/
│   └── sample/
│
├── config/
│
├── reports/
│
├── tests/
│
├── Dockerfile
├── Jenkinsfile
├── requirements.txt
├── README.md
└── PROJECT.md
```

---

# Outputs

The application generates:

- Terminal Report
- HTML Report
- JSON Report

Example:

```text
Dockerfile Security Report

Score: 85/100

Status: WARN

Findings:
✔ Base image specified
✖ USER root detected
✖ Missing HEALTHCHECK
✔ Valid Dockerfile syntax

Recommendations:
• Create a non-root user.
• Add a HEALTHCHECK instruction.
• Use a versioned image tag instead of 'latest'.
```

---

# Learning Outcomes

This project demonstrates knowledge of:

- Python Programming
- Docker
- Jenkins
- Git
- GitHub
- DevSecOps
- Cloud Security
- Container Security
- Static Configuration Analysis
- CI/CD Pipelines
- Software Architecture
- Modular Design
- Secure Software Development

---

# Future Enhancements

- Docker Compose scanning
- Kubernetes manifest scanning
- Secret detection
- PDF report generation
- REST API
- Authentication
- Dashboard analytics
- Plugin-based rule engine
- CIS Docker Benchmark support

---

# Conclusion

Dockerfile Security Checker is a lightweight DevSecOps security tool that helps developers identify insecure Dockerfile configurations before container images are built. By combining a reusable scanning engine with both CLI and Web interfaces, and integrating with GitHub, Jenkins, Docker, and Trivy, the project demonstrates a complete DevSecOps workflow focused on secure container development, automated security validation, and CI/CD pipeline integration.

---

**Intern ID:** CITS6600
