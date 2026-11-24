# Hindsight API (Slim)

Unofficial multi-architecture Docker Hub image of [vectorize-io/hindsight](https://github.com/vectorize-io/hindsight)'s API service.

This image is based on the ultra-lightweight **API Slim** variant (`vectorize-io/hindsight-api:latest-slim`), designed specifically for production deployments with **external services**:
- **External PostgreSQL + pgvector** (no bundled embedded database).
- **External LLM / Embedding / Reranking providers** (e.g. OpenAI, Anthropic, Ollama, vLLM, TEI).
- **Stateless & Scalable**: Strips embedded ML models, Next.js UI, and database binaries, resulting in a minimal container size, rapid startup, and zero local GPU/RAM overhead.

Upstream publishes official images at `ghcr.io/vectorize-io/hindsight-api`.
This Docker Hub build is not published or supported by Vectorize.

## Architectures And Tags

- `linux/amd64`: x86-64 Linux servers.
- `linux/arm64`: ARM64 Linux servers and Apple Silicon / ARM64 Docker hosts.
- `latest`, `latest-slim`, `slim`: latest stable upstream release.
- Version tags such as `1.3.0` and `1.3.0-slim`: corresponding upstream release without `v`.

## Quick Start

Connect to an existing PostgreSQL database with the `vector` extension installed:

```bash
docker run -d \
  --name hindsight-api \
  --restart unless-stopped \
  -p 127.0.0.1:8888:8888 \
  -e HINDSIGHT_API_DATABASE_URL="postgresql://user:password@pg-host:5432/hindsight" \
  -e HINDSIGHT_API_LLM_PROVIDER="openai" \
  -e HINDSIGHT_API_LLM_MODEL="gpt-4o-mini" \
  -e HINDSIGHT_API_LLM_API_KEY="your-api-key" \
  tozp/hindsight-api:latest-slim
```

API endpoint: `http://localhost:8888`

## Docker Compose Example

```yaml
services:
  hindsight-api:
    image: tozp/hindsight-api:latest-slim
    restart: unless-stopped
    ports:
      - "8888:8888"
    environment:
      HINDSIGHT_API_DATABASE_URL: postgresql://postgres:postgres@postgres:5432/hindsight
      HINDSIGHT_API_LLM_PROVIDER: openai
      HINDSIGHT_API_LLM_MODEL: gpt-4o-mini
      HINDSIGHT_API_LLM_API_KEY: ${OPENAI_API_KEY:?Set OPENAI_API_KEY}
    depends_on:
      postgres:
        condition: service_healthy

  postgres:
    image: pgvector/pgvector:pg16
    restart: unless-stopped
    environment:
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: postgres
      POSTGRES_DB: hindsight
    volumes:
      - pg-data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres"]
      interval: 5s
      timeout: 3s
      retries: 5

volumes:
  pg-data:
```

## Configuration

| Variable | Purpose |
| --- | --- |
| `HINDSIGHT_API_DATABASE_URL` | PostgreSQL connection string with pgvector extension. |
| `HINDSIGHT_API_LLM_PROVIDER` | LLM provider: `openai`, `anthropic`, `ollama`, etc. |
| `HINDSIGHT_API_LLM_MODEL` | Model identifier for generation/reflection tasks. |
| `HINDSIGHT_API_LLM_API_KEY` | Provider API key. |
| `HINDSIGHT_API_EMBEDDING_PROVIDER` | External embedding provider (if custom). |
| `HINDSIGHT_API_RERANKER_PROVIDER` | External reranker provider (if custom). |

For complete configuration options, visit the official [Hindsight Documentation](https://hindsight.vectorize.io/).
