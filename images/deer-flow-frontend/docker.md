# DeerFlow Frontend

Unofficial Docker Hub image of [bytedance/deer-flow](https://github.com/bytedance/deer-flow).
Built from stable upstream release tags using `frontend/Dockerfile`, target
`prod`, without modifying application source.

This image contains the production Next.js web frontend, not the Gateway API
or agent runtime. Use it with `tozp/deer-flow-gateway` and the upstream production
Compose stack. These images are not published or supported by ByteDance.

## Architectures And Tags

- `linux/amd64` and `linux/arm64`.
- `latest`: latest stable upstream GitHub Release successfully published here.
- Version tags such as `2.1.0`: corresponding upstream release without `v`.

Releases are checked hourly. Manual rebuilds of older releases do not move
`latest`. Pin matching version tags for the frontend and Gateway; pin image
digests for immutable deployments.

## Deployment

Use the [upstream configuration and Docker deployment guide](https://github.com/bytedance/deer-flow#quick-start)
from the same release as the images. Keep its configuration, environment,
volumes, commands, health checks, Redis, and nginx services. In
`docker/docker-compose.yaml`, replace only the frontend and Gateway `build`
sections with:

```yaml
services:
  frontend:
    image: tozp/deer-flow-frontend:2.1.0
  gateway:
    image: tozp/deer-flow-gateway:2.1.0
```

This fragment is not a standalone Compose file. Follow upstream setup to
prepare configuration and authentication secrets, including `BETTER_AUTH_SECRET`
and the frontend environment file. Keep
`DEER_FLOW_INTERNAL_GATEWAY_BASE_URL=http://gateway:8001` for the upstream
service topology. The optional Kubernetes provisioner and sandbox images are
not included in these builds.

The frontend listens on port `3000`. Access the application through the upstream
nginx entrypoint on port `2026`, bound to loopback by default. Do not expose the
agent publicly without authentication, TLS, and network restrictions.

## Upgrades

Back up persistent application data and review upstream release notes. Pull
matching frontend and Gateway versions and recreate their containers while
preserving the upstream configuration and data volumes.

- [Upstream releases](https://github.com/bytedance/deer-flow/releases)
- [Production Compose](https://github.com/bytedance/deer-flow/blob/main/docker/docker-compose.yaml)
- [Application issues](https://github.com/bytedance/deer-flow/issues)
- [License](https://github.com/bytedance/deer-flow/blob/main/LICENSE)