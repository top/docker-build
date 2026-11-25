# Hermes WebUI

Unofficial multi-architecture Docker Hub image of [nesquena/hermes-webui](https://github.com/nesquena/hermes-webui).

Upstream publishes official images at `ghcr.io/nesquena/hermes-webui`.
This Docker Hub build is not published or supported by Hermes WebUI.

## Architectures And Tags

- `linux/amd64`: x86-64 Linux servers.
- `linux/arm64`: ARM64 Linux servers and Apple Silicon / ARM64 Docker hosts.
- `latest`: latest stable upstream GitHub Release successfully published here.
- Version tags such as `0.52.732`: corresponding upstream release, without the `v` prefix.

## Quick Start

```bash
docker run -d \
  --name hermes-webui \
  --restart unless-stopped \
  -p 127.0.0.1:8787:8787 \
  -v "${HOME}/.hermes":/home/hermeswebui/.hermes \
  -v "${HOME}/workspace":/workspace \
  -e WANTED_UID="$(id -u)" \
  -e WANTED_GID="$(id -g)" \
  tozp/hermes-webui:latest
```

Open `http://localhost:8787`.

## Docker Compose

```yaml
services:
  hermes-webui:
    image: tozp/hermes-webui:latest
    restart: unless-stopped
    ports:
      - "127.0.0.1:8787:8787"
    volumes:
      - ${HERMES_HOME:-${HOME}/.hermes}:/home/hermeswebui/.hermes
      - ${HERMES_WORKSPACE:-${HOME}/workspace}:/workspace
    environment:
      - WANTED_UID=${UID:-1000}
      - WANTED_GID=${GID:-1000}
      - HERMES_WEBUI_HOST=0.0.0.0
      - HERMES_WEBUI_PORT=8787
      - HERMES_WEBUI_STATE_DIR=/home/hermeswebui/.hermes/webui
      - HERMES_WEBUI_PASSWORD=${HERMES_WEBUI_PASSWORD:-}
```

Start with `docker compose up -d`. For multi-container setups and full configuration options, refer to the [upstream repository](https://github.com/nesquena/hermes-webui).
