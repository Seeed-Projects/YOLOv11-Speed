# Docker Image Build Workflow

This GitHub Actions workflow automates the building and publishing of the YOLOv11 object detection Docker image to GitHub Container Registry.

## Workflow Overview

The workflow is defined in `.github/workflows/docker-image.yml` and consists of two main jobs:

### 1. `build-and-test` Job
- Runs on both push and pull request events
- Builds the Docker image without pushing
- Tests the built image by running `--help` command
- Ensures that the Docker image builds correctly before proceeding

### 2. `build-and-push` Job
- Runs only on push events (not pull requests)
- Builds and pushes the Docker image to GitHub Container Registry only
- Only runs after successful completion of the `build-and-test` job

## Triggers

The workflow is triggered by:
- Push events to `main` and `master` branches
- Push events with version tags (e.g., `v1.0.0`)
- Pull request events to `main` and `master` branches

## Docker Image Tags

The workflow generates several types of tags:
- `branch-name` (e.g., `main`, `feature-branch`)
- `pr-#` for pull requests (e.g., `pr-42`)
- SHA-based tags (e.g., `main-abc123d`)
- Semantic version tags for version tags (e.g., `v1.0.0`, `1.0`)
- `latest` tag for the main branch

## Required Secrets

The workflow uses the automatically available `GITHUB_TOKEN` for pushing to GitHub Container Registry. No additional secrets are required.

## Image Registry

The built images are pushed to:
- GitHub Container Registry: `ghcr.io/${{ github.repository }}`

## Platform Support

The image is built for `linux/amd64` platform. This can be extended to support other platforms if needed.

## Caching

The workflow uses GitHub Actions cache to speed up builds by caching Docker layers between runs.