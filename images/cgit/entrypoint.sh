#!/bin/sh
set -eu

CGIT_PORT="${CGIT_PORT:-80}"
CGIT_SCAN_PATH="${CGIT_SCAN_PATH:-/srv/git}"
CGIT_ROOT_TITLE="${CGIT_ROOT_TITLE:-Git Repositories}"
CGIT_ROOT_DESC="${CGIT_ROOT_DESC:-Fast web interface for Git repositories}"
CGIT_LOGO="${CGIT_LOGO:-/cgit.png}"
CGIT_LOGO_LINK="${CGIT_LOGO_LINK:-/}"
CGIT_CSS="${CGIT_CSS:-/cgit.css}"
CGIT_FAVICON="${CGIT_FAVICON:-/favicon.ico}"
CGIT_ENABLE_HTTP_CLONE="${CGIT_ENABLE_HTTP_CLONE:-1}"
CGIT_ENABLE_SYNTAX_HIGHLIGHT="${CGIT_ENABLE_SYNTAX_HIGHLIGHT:-1}"
CGIT_MAX_STATS="${CGIT_MAX_STATS:-quarter}"
CGIT_SIDE_BY_SIDE_DIFFS="${CGIT_SIDE_BY_SIDE_DIFFS:-0}"
CGIT_ENABLE_INDEX_OWNER="${CGIT_ENABLE_INDEX_OWNER:-1}"
CGIT_CACHE_SIZE="${CGIT_CACHE_SIZE:-1000}"
CGIT_CLONE_PREFIX="${CGIT_CLONE_PREFIX:-}"
CGIT_EXTRA_CONFIG="${CGIT_EXTRA_CONFIG:-}"

# Generate /etc/cgitrc unless user explicitly mounted their own
if [ ! -f /etc/cgitrc ]; then
    cat > /etc/cgitrc <<EOF
css=${CGIT_CSS}
logo=${CGIT_LOGO}
logo-link=${CGIT_LOGO_LINK}
favicon=${CGIT_FAVICON}
root-title=${CGIT_ROOT_TITLE}
root-desc=${CGIT_ROOT_DESC}
cache-size=${CGIT_CACHE_SIZE}
cache-root=/var/cache/cgit
enable-http-clone=${CGIT_ENABLE_HTTP_CLONE}
enable-index-owner=${CGIT_ENABLE_INDEX_OWNER}
max-stats=${CGIT_MAX_STATS}
side-by-side-diffs=${CGIT_SIDE_BY_SIDE_DIFFS}
enable-git-config=1
virtual-root=/
EOF

    if [ -n "$CGIT_CLONE_PREFIX" ]; then
        echo "clone-prefix=${CGIT_CLONE_PREFIX}" >> /etc/cgitrc
    fi

    if [ "$CGIT_ENABLE_SYNTAX_HIGHLIGHT" = "1" ]; then
        echo "source-filter=/usr/lib/cgit/filters/syntax-highlighting.sh" >> /etc/cgitrc
    fi

    if [ -n "$CGIT_EXTRA_CONFIG" ]; then
        printf '%s\n' "$CGIT_EXTRA_CONFIG" >> /etc/cgitrc
    fi

    # scan-path must come after global settings (like source-filter) in cgitrc
    echo "scan-path=${CGIT_SCAN_PATH}" >> /etc/cgitrc
fi

# Generate lighttpd configuration
cat > /etc/lighttpd/lighttpd.conf <<EOF
server.modules = (
    "mod_alias",
    "mod_cgi",
    "mod_rewrite",
    "mod_setenv"
)

server.document-root = "/usr/share/webapps/cgit"
server.port = ${CGIT_PORT}
server.bind = "0.0.0.0"

mimetype.assign = (
    ".css" => "text/css",
    ".js"  => "application/javascript",
    ".png" => "image/png",
    ".jpg" => "image/jpeg",
    ".svg" => "image/svg+xml",
    ".ico" => "image/x-icon",
    ".txt" => "text/plain"
)

alias.url = (
    "/_git_http" => "/usr/libexec/git-core/git-http-backend"
)

url.rewrite-once = (
    "^/(cgit\.css|cgit\.js|cgit\.png|favicon\.ico|robots\.txt|custom-logo\..*)$" => "/\$1",
    "^/(.*)/(HEAD|info/refs|objects/(info/[^/]+|pack/pack-[0-9a-f]+\.(pack|idx))|git-upload-pack)$" => "/_git_http/\$1/\$2",
    "^/(.*)$" => "/cgit.cgi/\$1"
)

\$HTTP["url"] =~ "^/_git_http" {
    setenv.add-environment = (
        "GIT_PROJECT_ROOT" => "${CGIT_SCAN_PATH}",
        "GIT_HTTP_EXPORT_ALL" => "1"
    )
    cgi.assign = ( "" => "" )
}

\$HTTP["url"] =~ "^/cgit\.cgi" {
    cgi.assign = ( "" => "" )
}
EOF

exec lighttpd -D -f /etc/lighttpd/lighttpd.conf
