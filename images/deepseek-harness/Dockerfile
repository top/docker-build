# syntax=docker/dockerfile:1
FROM node:24-bookworm-slim AS builder

WORKDIR /app

ENV CI=true \
    LEFTHOOK=0

RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 \
    make \
    g++ \
    git \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

RUN corepack enable && corepack prepare pnpm@latest --activate

COPY . .

# Patch browser-auth.ts to honor DSH_WEB_TOKEN from environment for persistent authentication
RUN if [ -f packages/client/connection/src/browser-auth.ts ]; then \
      sed -i 's/function processLaunchToken(owner: object): string {/function processLaunchToken(owner: object): string {\n  if (process.env.DSH_WEB_TOKEN) return process.env.DSH_WEB_TOKEN;/' \
        packages/client/connection/src/browser-auth.ts; \
    fi

# Clean dormant git worktree config if present to avoid hook conflicts
RUN rm -f .git/config.worktree 2>/dev/null || true

RUN pnpm install && pnpm run build

FROM node:24-bookworm-slim AS runner

WORKDIR /app

ENV CI=true \
    LEFTHOOK=0

RUN apt-get update && apt-get install -y --no-install-recommends \
    bash \
    git \
    curl \
    ca-certificates \
    python3 \
    procps \
    net-tools \
    && rm -rf /var/lib/apt/lists/*

RUN corepack enable && corepack prepare pnpm@latest --activate

RUN mkdir -p /workspace /home/node/.dsh && \
    chown -R node:node /workspace /home/node/.dsh

COPY --chown=node:node --from=builder /app /app

RUN cat <<'EOF' > /usr/local/bin/dsh
#!/usr/bin/env bash
if [ -f /app/apps/cli/lib/bin.js ]; then
  exec node /app/apps/cli/lib/bin.js "$@"
else
  exec pnpm --dir /app dsh "$@"
fi
EOF
RUN chmod +x /usr/local/bin/dsh

RUN cat <<'EOF' > /usr/local/bin/dsh-web-relay.js
const net = require('net');

const listenPort = parseInt(process.argv[2] || '3080', 10);
const targetPort = parseInt(process.argv[3] || '3081', 10);
const targetHost = '127.0.0.1';

const activeSockets = new Set();

const server = net.createServer((clientSocket) => {
  activeSockets.add(clientSocket);
  const targetSocket = net.connect({ host: targetHost, port: targetPort }, () => {
    clientSocket.pipe(targetSocket);
    targetSocket.pipe(clientSocket);
  });

  clientSocket.on('close', () => activeSockets.delete(clientSocket));
  targetSocket.on('close', () => activeSockets.delete(clientSocket));
  clientSocket.on('error', () => {
    targetSocket.destroy();
    activeSockets.delete(clientSocket);
  });
  targetSocket.on('error', () => {
    clientSocket.destroy();
    activeSockets.delete(clientSocket);
  });
});

server.on('error', (err) => {
  console.error('[relay] Server error:', err.message);
});

server.listen(listenPort, '0.0.0.0', () => {
  console.log(`[relay] Forwarding 0.0.0.0:${listenPort} -> ${targetHost}:${targetPort}`);
});

function shutdown() {
  server.close();
  for (const socket of activeSockets) {
    socket.destroy();
  }
}

process.on('SIGTERM', shutdown);
process.on('SIGINT', shutdown);
EOF

RUN cat <<'EOF' > /usr/local/bin/entrypoint.sh
#!/usr/bin/env bash
set -euo pipefail

DSH_DIR="${DSH_HOME:-/home/node/.dsh}"
mkdir -p "$DSH_DIR" "${DSH_WORKSPACE:-/workspace}"

TOKEN_FILE="$DSH_DIR/web_token"

if [[ -n "${DSH_WEB_TOKEN:-}" ]]; then
  printf '%s' "$DSH_WEB_TOKEN" > "$TOKEN_FILE"
  chmod 600 "$TOKEN_FILE" 2>/dev/null || true
  echo "[entrypoint] Using DSH_WEB_TOKEN from environment."
elif [[ -f "$TOKEN_FILE" ]] && [[ -s "$TOKEN_FILE" ]]; then
  DSH_WEB_TOKEN="$(cat "$TOKEN_FILE" | tr -d '\r\n[:space:]')"
  export DSH_WEB_TOKEN
  echo "[entrypoint] Reusing persistent web token from $TOKEN_FILE."
else
  DSH_WEB_TOKEN="$(node -e 'console.log(require("crypto").randomBytes(24).toString("hex"))')"
  export DSH_WEB_TOKEN
  printf '%s' "$DSH_WEB_TOKEN" > "$TOKEN_FILE"
  chmod 600 "$TOKEN_FILE" 2>/dev/null || true
  echo "[entrypoint] Generated new persistent web token in $TOKEN_FILE."
fi

PORT="${DSH_PORT:-3080}"
INTERNAL_PORT="3081"

EXTRA_ARGS=()
if [[ -n "${DSH_TRUSTED_HOSTS:-}" ]]; then
  IFS=',' read -ra HOSTS <<< "$DSH_TRUSTED_HOSTS"
  for host in "${HOSTS[@]}"; do
    host="$(echo "$host" | xargs)"
    if [[ -n "$host" ]]; then
      EXTRA_ARGS+=(--trusted-host "$host")
    fi
  done
fi

echo "=========================================================="
echo " DeepSeek Harness Web UI"
echo " Web UI Port:     $PORT"
echo " Persistent Token: $DSH_WEB_TOKEN"
echo " Open in Browser: http://localhost:${PORT}/?token=${DSH_WEB_TOKEN}"
echo "=========================================================="

node /usr/local/bin/dsh-web-relay.js "$PORT" "$INTERNAL_PORT" &
RELAY_PID=$!

cleanup() {
  echo "[entrypoint] Shutting down DeepSeek Harness..."
  kill -TERM "$RELAY_PID" 2>/dev/null || true
  if [[ -n "${DSH_PID:-}" ]]; then
    kill -TERM "$DSH_PID" 2>/dev/null || true
    wait "$DSH_PID" 2>/dev/null || true
  fi
  exit 0
}
trap cleanup SIGINT SIGTERM EXIT

cd "${DSH_WORKSPACE:-/workspace}"
if [ -f /app/apps/cli/lib/bin.js ]; then
  node /app/apps/cli/lib/bin.js web --port "$INTERNAL_PORT" --no-open "${EXTRA_ARGS[@]}" &
else
  pnpm --dir /app dsh web --port "$INTERNAL_PORT" --no-open "${EXTRA_ARGS[@]}" &
fi
DSH_PID=$!

wait "$DSH_PID"
EOF
RUN chmod +x /usr/local/bin/entrypoint.sh

USER node
ENV HOME=/home/node \
    DSH_HOME=/home/node/.dsh \
    DSH_WORKSPACE=/workspace \
    DSH_PORT=3080

WORKDIR /workspace

EXPOSE 3080

ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]
