# DeepSeek Harness

Unofficial multi-architecture image of [deepseek-ai/deepseek-harness](https://github.com/deepseek-ai/deepseek-harness),
an open-source developer harness and AI coding agent framework.

This image is not published or supported by DeepSeek.

## Architectures And Tags

- `linux/amd64`: x86-64 Linux servers.
- `linux/arm64`: ARM64 Linux servers and Apple Silicon / ARM64 Docker hosts.
- `latest`: latest stable upstream release successfully built and published here.
- Version tags such as `0.2.1-rc.5`: corresponding upstream release, without the `v` prefix.

Docker automatically selects the architecture matching your host. Upstream releases are checked hourly; publication can take additional time.

## Quick Start

```bash
docker run -d \
  --name deepseek-harness \
  --restart unless-stopped \
  -p 127.0.0.1:3080:3080 \
  -v dsh-data:/home/node/.dsh \
  -v "$(pwd)":/workspace \
  tozp/deepseek-harness:latest
```

View the startup logs to get your persistent login token:

```bash
docker logs deepseek-harness
```

Open `http://localhost:3080/?token=<YOUR_TOKEN>`. On first access, the token is exchanged for an authenticated browser session cookie.

## Docker Compose

```yaml
services:
  deepseek-harness:
    image: tozp/deepseek-harness:latest
    restart: unless-stopped
    ports:
      - "127.0.0.1:3080:3080"
    environment:
      # Optional: set a custom static token. If unset, an auto-generated token is persisted to dsh-data.
      # DSH_WEB_TOKEN: "your-custom-secure-token"
      DSH_PORT: 3080
    volumes:
      - dsh-data:/home/node/.dsh
      - ./:/workspace

volumes:
  dsh-data:
    name: dsh-data
```

Start with:

```bash
docker compose up -d
docker compose logs deepseek-harness
```

## Persistent Token & Data Management

- **Persistent Token**: When launched without an explicit `DSH_WEB_TOKEN`, the entrypoint generates a secure 48-character hex token and saves it to `/home/node/.dsh/web_token`. On subsequent container restarts, the exact same token is reloaded from the mounted volume, so your bookmark and login URL never change.
- **Custom Token**: Pass `DSH_WEB_TOKEN=...` in your environment or compose file to enforce your own token.
- **Skills, Extensions & History**: All plugin configurations, installed skills, model provider settings, and agent session history are preserved across container updates within the mounted `dsh-data` volume (`/home/node/.dsh`).
- **Workspace**: Mount your project root to `/workspace` so the agent can read, write, and run git commands on your files.

## Configuration

| Variable | Default | Purpose |
| --- | --- | --- |
| `DSH_WEB_TOKEN` | *auto-generated* | Static Web UI access token. Persisted in `/home/node/.dsh/web_token` if unset. |
| `DSH_TRUSTED_HOSTS` | *none* | Comma-separated list of allowed host headers (e.g. LAN IP or domain). |
| `DSH_PORT` | `3080` | Public container HTTP port. |
| `DSH_HOME` | `/home/node/.dsh` | Directory holding configurations, plugins, and session state. |
| `DSH_WORKSPACE` | `/workspace` | Default workspace working directory for the AI agent. |
