#!/usr/bin/env bash
set -euo pipefail

curl -fsSL --retry 3 https://github.com/mikefarah/yq/releases/download/v4.45.4/yq_linux_amd64 -o "$RUNNER_TEMP/yq"
echo "b96de04645707e14a12f52c37e6266832e03c29e95b9b139cddcae7314466e69  $RUNNER_TEMP/yq" | sha256sum --check
chmod +x "$RUNNER_TEMP/yq"
echo "$RUNNER_TEMP" >> "$GITHUB_PATH"