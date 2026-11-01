#!/usr/bin/env bash
set -euo pipefail

config="$1"
: "${DOCKERHUB_USERNAME:?Missing Docker Hub username}"
: "${DOCKERHUB_TOKEN:?Missing Docker Hub token}"
: "${GITHUB_OUTPUT:?Missing GitHub Actions output file}"

upstream="$(yq -er '."x-upstream"' "$config")"
[[ "$upstream" =~ ^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$ ]]
latest="$(gh api "repos/$upstream/releases/latest" --jq .tag_name)"
tag="${REQUESTED_TAG:-$latest}"
if [[ "$tag" =~ ^[0-9] && "$latest" == v* ]]; then
  tag="v$tag"
fi
version="${tag#v}"
if [[ ! "$tag" =~ ^v?[0-9][A-Za-z0-9_.-]*$ || ${#version} -gt 128 ]]; then
  echo "::error::Upstream tag is not a supported Docker version tag." >&2
  exit 1
fi
is_latest=false
if [[ "$tag" == "$latest" ]]; then is_latest=true; fi

export VERSION="$version"
export UPSTREAM_CONTEXT="${UPSTREAM_CONTEXT:-$PWD/upstream}"
bake="$(docker buildx bake -f "$config" --print)"
jq -e --arg prefix "$DOCKERHUB_USERNAME/" --arg suffix ":$version" '
  (.target | keys == ["image"]) and
  (.target.image.tags | length == 1 and
    all(.[]; startswith($prefix) and endswith($suffix) and
      test("^[a-z0-9]+[a-z0-9_-]*/[a-z0-9]+([._-][a-z0-9]+)*:[A-Za-z0-9_.-]+$"))) and
  (.target.image.platforms | type == "array" and length > 0 and
    all(.[]; test("^linux/[a-z0-9_]+(/[a-z0-9_]+)?$")))
' <<< "$bake" > /dev/null
image="$(jq -r '.target.image.tags[0] | split(":")[0]' <<< "$bake")"
platforms="$(jq -c '.target.image.platforms' <<< "$bake")"

manifest() {
  local response status body
  response="$(curl --silent --show-error --retry 3 --retry-all-errors \
    --header "Authorization: Bearer $registry_token" \
    --header 'Accept: application/vnd.oci.image.index.v1+json, application/vnd.docker.distribution.manifest.list.v2+json, application/vnd.oci.image.manifest.v1+json, application/vnd.docker.distribution.manifest.v2+json' \
    --write-out $'\n%{http_code}' \
    "https://registry-1.docker.io/v2/$image/manifests/$1")" || return
  status="${response##*$'\n'}"
  body="${response%$'\n'*}"
  case "$status" in
    200)
      printf '%s' "$body" | jq -cesS '
        def descriptor: type == "object" and (.digest | type == "string" and length > 0);
        if length != 1 then error("Expected one registry manifest") else .[0] |
          if type == "object" and .schemaVersion == 2 and
            (if has("manifests") then
              (.manifests | type == "array" and all(.[]; descriptor and
                (.platform == null or (.platform | type == "object" and
                  (.os | type == "string") and (.architecture | type == "string")))))
            else
              (.config | descriptor) and (.layers | type == "array" and all(.[]; descriptor))
            end)
          then . else error("Invalid registry manifest") end
        end'
      ;;
    404)
      printf '%s' "$body" | jq -e 'any(.errors[]?; .code == "MANIFEST_UNKNOWN" or .code == "NAME_UNKNOWN")' > /dev/null
      ;;
    *) echo "::error::Registry query for $image:$1 failed (HTTP $status)." >&2; return 1 ;;
  esac
}

should_build=true
repair_latest=false
if [[ "${GITHUB_EVENT_NAME:-}" != workflow_dispatch ]]; then
  registry_token="$(curl --fail --silent --show-error --retry 3 --retry-all-errors \
    --user "$DOCKERHUB_USERNAME:$DOCKERHUB_TOKEN" \
    --get --data-urlencode service=registry.docker.io \
    --data-urlencode "scope=repository:$image:pull" \
    https://auth.docker.io/token | jq -er '.token | strings | select(length > 0)')"
  echo "::add-mask::$registry_token"
  published="$(manifest "$version")"
  if [[ -n "$published" ]] && jq -e --argjson required "$platforms" '
    . as $manifest | all($required[];
      split("/") as $parts | any($manifest.manifests[]?;
        .platform.os == $parts[0] and .platform.architecture == $parts[1] and
        (($parts | length) < 3 or .platform.variant == $parts[2])))
  ' <<< "$published" > /dev/null; then
    should_build=false
    if [[ "$is_latest" == true ]]; then
      current_latest="$(manifest latest)"
      if [[ "$current_latest" != "$published" ]]; then repair_latest=true; fi
    fi
  fi
fi

{
  echo "upstream=$upstream"
  echo "image=$image"
  echo "tag=$tag"
  echo "version=$version"
  echo "should_build=$should_build"
  echo "repair_latest=$repair_latest"
  echo 'tags<<TAGS'
  echo "image.tags=$image:$version"
  if [[ "$is_latest" == true ]]; then echo "image.tags+=$image:latest"; fi
  echo TAGS
} >> "$GITHUB_OUTPUT"
printf '%s: upstream=%s build=%s repair_latest=%s\n' "$image" "$tag" "$should_build" "$repair_latest"