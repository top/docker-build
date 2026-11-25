# nanoMuse Cloud (Relay)

Unofficial multi-architecture Docker Hub image of [nano-muse/nanoMuse](https://github.com/nano-muse/nanoMuse)'s self-hosted relay server (`cloud/Dockerfile`).

Upstream does not publish pre-built container images for the `nanomuse-cloud` relay; this image is built directly from upstream release tags for both `linux/amd64` and `linux/arm64`.

## Architectures And Tags

- `linux/amd64`: x86-64 Linux servers.
- `linux/arm64`: ARM64 Linux servers and Apple Silicon / ARM64 Docker hosts.
- `latest`: latest stable upstream GitHub Release successfully published here.
- Version tags such as `1.0.9`: corresponding upstream release, without the `v` prefix.

## Quick Start

The relay stores its SQLite database at `/srv/nanomuse-cloud/data` and runs as UID/GID `10001` (`relay`):

```bash
mkdir -p ./data
chown -R 10001:10001 ./data

docker run -d \
  --name nanomuse-cloud \
  --restart unless-stopped \
  -p 127.0.0.1:8787:8787 \
  -v "$(pwd)/data":/srv/nanomuse-cloud/data \
  --env-file .env \
  tozp/nanomuse-cloud:latest
```

## Docker Compose (with Caddy TLS)

```yaml
services:
  relay:
    image: tozp/nanomuse-cloud:latest
    restart: unless-stopped
    env_file:
      - path: .env
        required: false
    volumes:
      - ./data:/srv/nanomuse-cloud/data
    expose:
      - "8787"

  caddy:
    image: caddy:2
    restart: unless-stopped
    ports:
      - "80:80"
      - "443:443"
    environment:
      CLOUD_DOMAIN: ${CLOUD_DOMAIN:-localhost}
      ACME_EMAIL: ${ACME_EMAIL:-}
    volumes:
      - ./Caddyfile:/etc/caddy/Caddyfile:ro
      - caddy_data:/data
      - caddy_config:/config
    depends_on:
      - relay

volumes:
  caddy_data:
  caddy_config:
```

For environment variables (`.env`), `Caddyfile`, and full self-hosting instructions, refer to upstream's [`cloud/`](https://github.com/nano-muse/nanoMuse/tree/main/cloud) directory and [`docs/self-hosting.md`](https://github.com/nano-muse/nanoMuse/blob/main/docs/self-hosting.md).
