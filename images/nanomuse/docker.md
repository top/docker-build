# nanoMuse

Unofficial multi-architecture Docker Hub image of [nano-muse/nanoMuse](https://github.com/nano-muse/nanoMuse).

Upstream publishes official images at `ghcr.io/nano-muse/nanomuse`.
This Docker Hub build is not published or supported by nanoMuse.

## Architectures And Tags

- `linux/amd64`: x86-64 Linux servers.
- `linux/arm64`: ARM64 Linux servers and Apple Silicon / ARM64 Docker hosts.
- `latest`: latest stable upstream GitHub Release successfully published here.
- Version tags such as `1.0.9`: corresponding upstream release, without the `v` prefix.

## Quick Start

Run the web console and API server on port `8787`:

```bash
docker run -d \
  --name nanomuse \
  --restart unless-stopped \
  -p 127.0.0.1:8787:8787 \
  -v nanomuse-data:/data \
  -v "$(pwd)/workspace":/workspace \
  tozp/nanomuse:latest \
  serve --host 0.0.0.0 --no-qr
```

## Docker Compose

```yaml
services:
  nanomuse:
    image: tozp/nanomuse:latest
    restart: unless-stopped
    command: ["serve", "--host", "0.0.0.0", "--no-qr"]
    ports:
      - "127.0.0.1:8787:8787"
    env_file:
      - path: .env
        required: false
    volumes:
      - nanomuse-data:/data
      - ./workspace:/workspace
      - ./config/config.toml:/app/config/config.toml:ro
    security_opt:
      - no-new-privileges:true
    cap_drop:
      - ALL

volumes:
  nanomuse-data:
```

Start with `docker compose up -d`. For full setup instructions (API keys, `NANOMUSE_SERVER_TOKEN`, `config.toml`), refer to the [upstream repository](https://github.com/nano-muse/nanoMuse).
