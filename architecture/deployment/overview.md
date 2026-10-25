# Deployment & Operations

Infrastructure for deployment and operations.

## Overview

| Component | Description |
|-----------|-------------|
| [Operator CLI](cli.md) | The standalone `devlog` command surface |
| [Managed Deployment](managed-deployment.md) | systemd units, compose/proxy rendering, drift, lifecycle |
| [Installation](installation.md) | Installation modes, responsibility boundaries, path resolution |
| [Docker](docker.md) | Container orchestration |
| [CI/CD](cicd.md) | Testing and deployment pipelines |
| [Security](security.md) | Security architecture |

## See Also
- [Operator CLI](cli.md) - The `devlog` command groups, Result model and exit codes
- [Managed Deployment](managed-deployment.md) - Rendering and installing host-level configuration
- [Installation](installation.md) - Installer/onboarding responsibility boundary, RuntimePaths, legacy migration
- [Docker](docker.md) - Container setup
- [CI/CD](cicd.md) - GitHub Actions workflows
- [Security](security.md) - Authentication, CSRF, etc.
