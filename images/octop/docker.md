# Octop

Unofficial multi-architecture image of [TencentCloud/Octop](https://github.com/TencentCloud/Octop),
a self-hosted AI assistant. Built from upstream release tags using the upstream
`docker/Dockerfile`, without modifying application source.

This image is not published or supported by TencentCloud.

## Architectures And Tags

- `linux/amd64`: x86-64 Linux servers.
- `linux/arm64`: ARM64 Linux servers and ARM64 Docker hosts.
- `latest`: latest stable upstream GitHub Release successfully published here.
- Version tags such as `1.0.2`: corresponding upstream release, without the `v` prefix.

Docker automatically selects the architecture matching your host. Upstream
releases are checked hourly; publication can take additional time. Pin a version
tag for controlled upgrades. Tags can be replaced by manual rebuilds; use an
image digest when immutable deployment references are required.

Manually rebuilding an older release does not move `latest`. If a completed
version is already published, a stale `latest` is repaired without rebuilding.

## Quick Start

```bash
docker run -d \
  --name octop \
  --restart unless-stopped \
  --ulimit nofile=65535:65535 \
  -p 127.0.0.1:8088:8088 \
  -e HOME=/data \
  -v octop-data:/data/.octop \
  tozp/octop:latest
```

Open `http://localhost:8088`. On a fresh installation, retrieve the setup wizard
unlock password locally:

```bash
docker exec octop cat /data/.octop/octop-login.txt
```

Complete the wizard to create the administrator and configure your model
provider. The wizard password is not an administrator login password.

Alternatively, pass `OCTOP_DEFAULT_PASSWORD` on first boot to create the initial
administrator automatically. It must contain at least eight characters,
including letters and digits, and must not be a common password. An unset or
rejected password falls back to the setup wizard. First-run login or setup
information is also stored in `/data/.octop/credential.txt`; treat these files
as secrets. Older release tags may have different bootstrap behavior.

## Docker Compose

```yaml
services:
  octop:
    image: tozp/octop:latest
    restart: unless-stopped
    ports:
      - "127.0.0.1:8088:8088"
    environment:
      HOME: /data
    volumes:
      - octop-data:/data/.octop
    ulimits:
      nofile:
        soft: 65535
        hard: 65535

volumes:
  octop-data:
    name: octop-data
```

Start with `docker compose up -d`. Retrieve the wizard password with
`docker compose exec octop cat /data/.octop/octop-login.txt`.

## Configuration

| Variable | Purpose |
| --- | --- |
| `HOME=/data` | Keeps application state under the mounted data directory. |
| `OCTOP_PORT` | Container HTTP port; defaults to `8088`. Update port mappings if changed. |
| `OCTOP_DEFAULT_PASSWORD` | Optional first-run administrator password. Not a password reset mechanism. |
| `OCTOP_ADMIN_USERNAME` | Initial administrator username; defaults to `admin`. |
| `OPENAI_API_KEY` | API key for an OpenAI-compatible provider, where applicable. |
| `DASHSCOPE_API_KEY` | API key for Alibaba DashScope, where applicable. |
| `OCTOP_DATABASE_URL` | Optional external database connection string. |

See the [upstream configuration guide](https://github.com/TencentCloud/Octop/blob/main/docs/configuration.md)
for provider settings and external database configuration. Never include API
keys or passwords in a public Compose file.

## Persistence And Upgrades

Keep `/data/.octop` mounted. It contains application configuration, local
database state, credentials, and other application data. Back up the volume
before upgrading. If using an external database, back it up separately.

For Compose deployments:

```bash
docker compose pull
docker compose up -d
docker compose logs -f octop
```

For `docker run`, pull the desired image, remove the old container, and recreate
it with the same volume and settings. Do not remove the data volume.
`docker compose down -v` deletes the named volume and its data.

The upstream image health check probes `/api/health`. Inspect startup issues
with `docker logs octop`. Changing the initial password environment variable
does not change an existing administrator account's password.

## Network And Support

Examples bind to loopback only. For remote access, use an authenticated HTTPS
reverse proxy or a secured private network. Do not expose a fresh setup wizard
directly to the public Internet.

- [Upstream Docker deployment guide](https://github.com/TencentCloud/Octop/tree/main/docker)
- [Upstream releases](https://github.com/TencentCloud/Octop/releases)
- [Upstream application issues](https://github.com/TencentCloud/Octop/issues)
- [Upstream license](https://github.com/TencentCloud/Octop/blob/main/LICENSE)