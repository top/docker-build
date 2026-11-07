# DeepTutor

Unofficial Docker Hub image of [HKUDS/DeepTutor](https://github.com/HKUDS/DeepTutor),
an AI-powered personalized learning assistant and agent-native learning platform.

Built from stable upstream release tags using `Dockerfile`, target `production`,
without modifying application source. The image contains both the Next.js frontend
and FastAPI backend managed by Supervisor.

Upstream publishes official images at `ghcr.io/hkuds/deeptutor`.
This Docker Hub build is not published or supported by HKUDS.

## Architectures And Tags

- `linux/amd64`: x86-64 Linux servers.
- `linux/arm64`: ARM64 Linux servers and Apple Silicon / ARM64 Docker hosts.
- `latest`: latest stable upstream GitHub Release successfully built and published here.
- Version tags such as `1.7.2`: corresponding upstream release, without the `v` prefix.

Docker automatically selects your host architecture. Upstream releases are checked
hourly; publication can take additional time.

## Docker Compose

DeepTutor requires an internal Redis service for event coordination. Create a `docker-compose.yml` file:

```yaml
services:
  redis:
    image: redis:7.4-alpine
    container_name: deeptutor-redis
    restart: unless-stopped
    command: ["redis-server", "--appendonly", "yes", "--appendfsync", "everysec"]
    volumes:
      - ./data/redis:/data
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 5s
      timeout: 3s
      retries: 10
    networks:
      - deeptutor-network

  deeptutor:
    image: tozp/deeptutor:latest
    container_name: deeptutor
    restart: unless-stopped
    ports:
      - "8001:8001"
      - "3782:3782"
    volumes:
      - ./data:/app/data
      - ./data/user/workspace:/workspace
    environment:
      - DEEPTUTOR_WORKSPACE_ROOT=/workspace
      - DEEPTUTOR_WORKSPACE_ALLOWED_ROOTS=/workspace
      # Optional: allow restricted subprocess code execution without a sidecar runner
      - DEEPTUTOR_SANDBOX_ALLOW_SUBPROCESS=1
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8001/health/ready"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 60s
    depends_on:
      redis:
        condition: service_healthy
    networks:
      - deeptutor-network

networks:
  deeptutor-network:
    driver: bridge
```

Start the service:

```bash
docker compose up -d
```

- Web UI: `http://localhost:3782`
- Backend API: `http://localhost:8001`

## Configuration

| Variable | Default | Purpose |
| --- | --- | --- |
| `DEEPTUTOR_WORKSPACE_ROOT` | `/workspace` | Default workspace working directory inside container. |
| `DEEPTUTOR_WORKSPACE_ALLOWED_ROOTS` | `/workspace` | Allowed paths for file operations. |
| `DEEPTUTOR_SANDBOX_ALLOW_SUBPROCESS` | `1` | Enable restricted subprocess execution for shell and office tools. |
| `DEEPTUTOR_SANDBOX_RUNNER_URL` | *unset* | URL of an external sandbox runner sidecar (if deployed). |
| `PUID` / `PGID` | *unset* | Remap container user to host UID/GID for NAS / bind mounts. |

Model provider configurations (e.g. OpenAI, Anthropic, Ollama, LM Studio) can be configured directly in the web Settings UI or by editing `data/user/settings/model_catalog.json`.

## Persistence And Upgrades

All user settings, chat sessions, knowledge bases, and workspace contents are stored under the `./data` directory. Back up `./data` before upgrading.

To update to the latest image:

```bash
docker compose pull
docker compose up -d
```
