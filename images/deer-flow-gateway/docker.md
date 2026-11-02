# DeerFlow Gateway

Unofficial Docker Hub image of [bytedance/deer-flow](https://github.com/bytedance/deer-flow).
Built from stable upstream release tags using `backend/Dockerfile` and its
default production stage, without modifying application source.

This image contains the Gateway API and agent runtime, not the web frontend.
Use it with `tozp/deer-flow-frontend` and the upstream production Compose stack.
These images are not published or supported by ByteDance.

## Architectures And Tags

- `linux/amd64` and `linux/arm64`.
- `latest`: latest stable upstream GitHub Release successfully published here.
- Version tags such as `2.1.0`: corresponding upstream release without `v`.

Releases are checked hourly. Manual rebuilds of older releases do not move
`latest`. Pin matching version tags for the Gateway and frontend; pin image
digests for immutable deployments.

## Deployment

Use the [upstream configuration and Docker deployment guide](https://github.com/bytedance/deer-flow#quick-start)
from the same release as the images. Keep its configuration, environment,
volumes, commands, health checks, Redis, and nginx services. In
`docker/docker-compose.yaml`, replace only the Gateway and frontend `build`
sections with:

```yaml
services:
  gateway:
    image: tozp/deer-flow-gateway:2.1.0
  frontend:
    image: tozp/deer-flow-frontend:2.1.0
```

This fragment is not a standalone Compose file. Follow upstream setup to
prepare model credentials, configuration files, authentication secrets, and
runtime directories before starting services. The optional Kubernetes
provisioner and sandbox images are not included in these builds.

The Gateway listens on port `8001`. Keep access behind the upstream nginx
entrypoint, which publishes port `2026` on loopback by default. Do not expose
the agent publicly without authentication, TLS, and network restrictions.
Mounting the host Docker socket grants host root-equivalent access; enable
that optional overlay only when required by your sandbox configuration.

## Persistence And Upgrades

Preserve the upstream configuration and persistent data mounts. Back up data
and review release notes before upgrading. Pull matching Gateway and frontend
versions and recreate their containers without deleting volumes. Optional
backend dependencies require a custom build with upstream's `UV_EXTRAS` argument.

- [Upstream releases](https://github.com/bytedance/deer-flow/releases)
- [Configuration](https://github.com/bytedance/deer-flow/blob/main/backend/docs/CONFIGURATION.md)
- [Application issues](https://github.com/bytedance/deer-flow/issues)
- [License](https://github.com/bytedance/deer-flow/blob/main/LICENSE)