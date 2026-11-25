# Docker Hub Images

Configuration-driven, unofficial multi-architecture builds for open-source AI and developer tools. One hourly workflow discovers `images/*/build.yml`; each project independently checks its latest stable GitHub Release and publishes to Docker Hub.

## Local Build & Sync Wizard (`build.py`)

To avoid exhausting GitHub Actions free-tier runner minutes (especially under QEMU ARM64 cross-compilation), you can run the interactive wizard locally on macOS, Linux, or Windows. Any machine with Docker installed can run it without configuration:

```bash
python3 build.py
```

### Features
1. **Interactive Wizard (向导式交互)**: No CLI arguments required. Simply run the script, choose a project from the menu, and confirm.
2. **Automatic Upstream Querying**: Queries the official upstream GitHub repository in real time to fetch the latest stable release tag.
3. **GHCR Fast-Sync & Minimal Variant Priority**:
   - Before compiling locally, the wizard searches GitHub Container Registry (`ghcr.io`) for pre-built multi-arch images.
   - **Picks the smallest variant first**: Automatically prioritizes `alpine`, `slim`, and `minimal` tags if available.
   - Directly re-tags and pushes multi-architecture manifests (`linux/amd64`, `linux/arm64`) to Docker Hub via `docker buildx imagetools create` within seconds without downloading layers or rebuilding locally.
4. **Buildx Fallback**: If no pre-built image exists on GHCR, it automatically falls back to cloning source code and building multi-arch images locally with Docker Buildx.

You can also run non-interactively if needed:
```bash
python3 build.py deeptutor --tag 1.7.4 --yes
```

## Supported Images

| Project Directory | Target Repository | Upstream | Overview |
| --- | --- | --- | --- |
| `octop` | `${DOCKERHUB_USERNAME}/octop` | [TencentCloud/Octop](https://github.com/TencentCloud/Octop) | [docker.md](images/octop/docker.md) |
| `hindsight-api` | `${DOCKERHUB_USERNAME}/hindsight-api` | [vectorize-io/hindsight](https://github.com/vectorize-io/hindsight) | [docker.md](images/hindsight-api/docker.md) |
| `nanomuse` | `${DOCKERHUB_USERNAME}/nanomuse` | [nano-muse/nanoMuse](https://github.com/nano-muse/nanoMuse) | [docker.md](images/nanomuse/docker.md) |
| `hermes-webui` | `${DOCKERHUB_USERNAME}/hermes-webui` | [nesquena/hermes-webui](https://github.com/nesquena/hermes-webui) | [docker.md](images/hermes-webui/docker.md) |
| `deer-flow-gateway` | `${DOCKERHUB_USERNAME}/deer-flow-gateway` | [bytedance/deer-flow](https://github.com/bytedance/deer-flow) | [docker.md](images/deer-flow-gateway/docker.md) |
| `deer-flow-frontend` | `${DOCKERHUB_USERNAME}/deer-flow-frontend` | [bytedance/deer-flow](https://github.com/bytedance/deer-flow) | [docker.md](images/deer-flow-frontend/docker.md) |
| `deeptutor` | `${DOCKERHUB_USERNAME}/deeptutor` | [HKUDS/DeepTutor](https://github.com/HKUDS/DeepTutor) | [docker.md](images/deeptutor/docker.md) |

## Setup

1. Enable GitHub Actions in this repository. Private repositories are supported;
   GitHub-hosted runner usage counts against your plan's Actions allowance.
2. Create the destination repositories in your Docker Hub namespace for each project
   you wish to build (matching the project directory names in the table above).
3. Configure Actions secrets:
   - `DOCKERHUB_USERNAME`: Docker Hub username and destination namespace.
   - `DOCKERHUB_TOKEN`: personal access token with Read & Write permissions.
   - `DOCKERHUB_DESCRIPTION_TOKEN`: optional separate token with Read/Write/Delete
     permissions, required by the description-sync action. If omitted, that
     action uses `DOCKERHUB_TOKEN`, which then needs Read/Write/Delete permissions.
4. The Docker Hub examples use `tozp`; update the `docker.md` files if using
   another namespace. Never put credentials in project configuration files.
5. Run **Build multi-arch images** manually by specifying any project directory name
   (e.g. `deeptutor` or `octop`). DeerFlow's two images build independently; use matching
   version tags when deploying them together.

The workflow requires only read access to GitHub repository contents. It does
not commit versions, modify repository variables, or require branch push access.

## Updates

At minute 20 of each hour, a dynamic matrix checks every configured project.
A release is skipped only when its Docker Hub version tag contains every
configured platform. Missing tags or architectures trigger a build. Registry
authentication, rate-limit, and network errors fail the check instead of being
treated as missing images. Failed builds retry at the next scheduled check.

Successful builds publish a version tag without the leading `v`. Only the
latest stable release also publishes `latest`. If the version already exists
but `latest` differs, the workflow repairs `latest` without rebuilding.
Docker Hub is the source of publication state; no local version records exist.

Manual runs require a project directory name, not a fixed selection list.
Leave `tag` empty for the latest stable release, or enter an upstream version
such as `v1.0.2` or `1.0.2`. Manual runs always rebuild; older versions never
change `latest`. A version without `v` is prefixed when upstream's latest tag
uses that convention. Changes to build configuration under an existing version
require a manual rebuild. Moved upstream tags are not automatically detected.

Projects run independently with separate concurrency groups and cache scopes.
ARM64 uses QEMU on GitHub's x86-64 runner; full builds can take significant time
and disk space. Scheduled execution can be delayed by GitHub.

## Project Configuration

Each project directory contains only `build.yml` and `docker.md`. The build
file uses Docker Buildx Bake's Compose format with one service named `image`:

```yaml
x-upstream: TencentCloud/Octop

services:
   image:
      image: ${DOCKERHUB_USERNAME:?Set DOCKERHUB_USERNAME}/octop:${VERSION:-check}
      build:
         context: ${UPSTREAM_CONTEXT:?Set absolute UPSTREAM_CONTEXT}
         dockerfile: docker/Dockerfile
         platforms:
            - linux/amd64
            - linux/arm64
```

`x-upstream` is the GitHub `owner/repository` for stable Releases.
Optionally, specify `x-ghcr-image` to point to pre-built GHCR packages (e.g. `ghcr.io/vectorize-io/hindsight`),
and `x-variant-preference` (such as `slim` or `alpine`) to automatically prioritize lightweight variants.
The builder reads these configurations automatically without external dependencies.

The service's `image` is the sole image-name declaration; `build.platforms` is
the sole platform list. The checker reads both from `bake --print`. Standard
Compose `build` fields support `context`, `dockerfile`, optional `target`, and
`args`; build arguments are not for secrets. Octop omits `target` to use the
upstream Dockerfile's default final stage.

The workflow supplies `DOCKERHUB_USERNAME`, `UPSTREAM_CONTEXT` (the absolute
upstream checkout directory), and `VERSION` (the selected tag without `v`).
`VERSION` defaults to `check` when only reading metadata. Dockerfile paths are relative
to the build context, not the project configuration directory. For subdirectory
contexts, append the path to `${UPSTREAM_CONTEXT}` and adjust `dockerfile`.
Checks and builds run from the repository root with the same environment.

Add these two files to support another upstream Dockerfile build. Directory
names use lowercase letters, digits, underscores, and hyphens. Give each
project a distinct Docker Hub image name.

## Docker Hub Descriptions

Each `docker.md` is a standalone Docker Hub overview and may be pasted directly.
The workflow also syncs it independently of build success or release changes,
on scheduled/manual runs and pushes to `main` affecting project files or the
workflow. Push-triggered runs sync descriptions only, without building images.
Changing only a description does not require an image rebuild.

Description synchronization uses
[peter-evans/dockerhub-description](https://github.com/peter-evans/dockerhub-description).
Its token permission requirement is separate from image pushing; a description
failure does not cancel image builds.
