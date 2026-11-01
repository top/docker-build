# Hindsight

Unofficial Docker Hub image of [vectorize-io/hindsight](https://github.com/vectorize-io/hindsight),
an agent memory system with retain, recall, and reflect operations.

Built from upstream release tags using `docker/standalone/Dockerfile`, target
`standalone`, without modifying application source. The image includes the API,
web UI, embedded PostgreSQL support, and upstream's default local ML dependencies
and model preloading. This is the full image, not a slim variant.

Upstream publishes official images at `ghcr.io/vectorize-io/hindsight`.
This Docker Hub build is not published or supported by Vectorize.

## Architectures And Tags

- `linux/amd64`: x86-64 Linux servers.
- `linux/arm64`: ARM64 Linux servers and ARM64 Docker hosts.
- `latest`: latest stable upstream GitHub Release successfully published here.
- Version tags such as `1.1.0`: corresponding upstream release, without the `v` prefix.

Docker automatically selects your host architecture. Releases are checked
hourly; full multi-architecture builds can take significant time. Version tags
can be manually rebuilt. Pin an image digest for immutable deployments.

Manually rebuilding an older release does not move `latest`. If a completed
version is already published, a stale `latest` is repaired without rebuilding.

## Quick Start

Set your OpenAI API key in your local shell:

```bash
export OPENAI_API_KEY=your-api-key
```

Start the API and UI with persistent embedded database storage:

```bash
docker run -d \
  --name hindsight \
  --restart unless-stopped \
  -p 127.0.0.1:8888:8888 \
  -p 127.0.0.1:9999:9999 \
  -e HINDSIGHT_API_LLM_PROVIDER=openai \
  -e HINDSIGHT_API_LLM_MODEL=gpt-4o-mini \
  -e HINDSIGHT_API_LLM_API_KEY="$OPENAI_API_KEY" \
  -v hindsight-data:/home/hindsight/.pg0 \
  tozp/hindsight:latest
```

- API base URL: `http://localhost:8888`.
- Web UI: `http://localhost:9999`.

The example selects an OpenAI model explicitly; choose a model supported by your
provider and account. A model provider is still needed for LLM operations even
though local embedding and reranking dependencies are bundled.

## Docker Compose

Set `OPENAI_API_KEY` in your shell or a local `.env` file. Do not commit the key.

```yaml
services:
  hindsight:
    image: tozp/hindsight:latest
    restart: unless-stopped
    ports:
      - "127.0.0.1:8888:8888"
      - "127.0.0.1:9999:9999"
    environment:
      HINDSIGHT_API_LLM_PROVIDER: openai
      HINDSIGHT_API_LLM_MODEL: gpt-4o-mini
      HINDSIGHT_API_LLM_API_KEY: ${OPENAI_API_KEY:?Set OPENAI_API_KEY}
    volumes:
      - hindsight-data:/home/hindsight/.pg0

volumes:
  hindsight-data:
    name: hindsight-data
```

Start with `docker compose up -d`. Follow startup with
`docker compose logs -f hindsight`. Initial startup may take time while the
database is initialized and models are loaded.

## Configuration

| Variable | Purpose |
| --- | --- |
| `HINDSIGHT_API_LLM_PROVIDER` | LLM provider, such as `openai`, `anthropic`, or `ollama`. |
| `HINDSIGHT_API_LLM_MODEL` | Model identifier supported by the selected provider. |
| `HINDSIGHT_API_LLM_API_KEY` | Provider API key, when required. |

Provider-specific settings, external databases, authentication, and model
options are documented upstream:

- [Installation](https://hindsight.vectorize.io/developer/installation)
- [Configuration](https://hindsight.vectorize.io/developer/configuration)
- [Supported models and providers](https://hindsight.vectorize.io/developer/models)
- [Storage](https://hindsight.vectorize.io/developer/storage)

When connecting to another container, use its network service name rather than
`localhost`. Inside this container, `localhost` refers to Hindsight itself.

## Persistence And Upgrades

Mount `/home/hindsight/.pg0` to preserve the embedded database. A named volume is
recommended; bind mounts must be writable by the upstream image's `hindsight`
user. If using an external database, back up that database separately.

Before upgrades, back up your data and review upstream release notes. Do not
copy a running database's files as though they were a consistent backup; use
database-aware backups or stop the service before taking a filesystem backup.

```bash
docker compose pull
docker compose up -d
docker compose logs -f hindsight
```

For `docker run`, recreate the container with the new image, the same volume,
and the same configuration. Do not delete the data volume.
`docker compose down -v` removes the named volume and its database.

## Network And Support

Examples expose the API and UI only on loopback. Do not assume either endpoint
is safe to publish without authentication. Use an authenticated HTTPS reverse
proxy or a secured private network and follow upstream's production guidance.

The full image bundles ML dependencies and can be large. Ensure sufficient disk
space and memory; actual resource requirements depend on models and workload.

- [Upstream releases](https://github.com/vectorize-io/hindsight/releases)
- [API reference](https://hindsight.vectorize.io/api-reference)
- [Upstream application issues](https://github.com/vectorize-io/hindsight/issues)
- [Upstream license](https://github.com/vectorize-io/hindsight/blob/main/LICENSE)