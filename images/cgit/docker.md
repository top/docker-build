# cgit

Minimal multi-architecture Docker Hub image for [cgit](https://git.zx2c4.com/cgit) — a hyperfast web interface for Git repositories written in C.

Built on Alpine Linux with `lighttpd` (`mod_cgi`), `git-http-backend` (for `git clone` over HTTP), and `highlight` (for lightweight server-side syntax highlighting without Python).

## Architectures And Tags

- `linux/amd64`: x86-64 Linux servers.
- `linux/arm64`: ARM64 Linux servers and Apple Silicon / ARM64 Docker hosts.
- `latest`: latest stable upstream release.
- Version tags such as `1.3.1`: corresponding upstream release, without the `v` prefix.

## Quick Start

Mount a parent directory containing your bare Git repositories to `/srv/git`:

```bash
docker run -d \
  --name cgit \
  --restart unless-stopped \
  -p 8080:80 \
  -v /path/to/your/git-repos:/srv/git:ro \
  -e CGIT_ROOT_TITLE="My Git Repositories" \
  -e CGIT_ROOT_DESC="Self-hosted Git mirrors and projects" \
  tozp/cgit:latest
```

Open `http://localhost:8080`, or clone a repository directly:

```bash
git clone http://localhost:8080/my-repo.git
```

## Docker Compose

```yaml
services:
  cgit:
    image: tozp/cgit:latest
    restart: unless-stopped
    ports:
      - "8080:80"
    environment:
      CGIT_ROOT_TITLE: "My Git Repositories"
      CGIT_ROOT_DESC: "Lightweight Git web frontend"
      CGIT_CLONE_PREFIX: "https://git.example.com"
      CGIT_ENABLE_HTTP_CLONE: "1"
      CGIT_ENABLE_SYNTAX_HIGHLIGHT: "1"
    volumes:
      - ./repos:/srv/git:ro
      # Optional: mount a custom logo image and point CGIT_LOGO to /custom-logo.png
      # - ./logo.png:/usr/share/webapps/cgit/custom-logo.png:ro
      # Optional: mount a full custom cgitrc (overrides env var generation)
      # - ./cgitrc:/etc/cgitrc:ro
```

## Configuration (Environment Variables)

If `/etc/cgitrc` is not mounted, the entrypoint generates it automatically from these environment variables:

| Variable | Default | Purpose |
| --- | --- | --- |
| `CGIT_SCAN_PATH` | `/srv/git` | Root directory scanned for Git repositories (also `GIT_PROJECT_ROOT` for HTTP clone). |
| `CGIT_ROOT_TITLE` | `Git Repositories` | Main page title. |
| `CGIT_ROOT_DESC` | `Fast web interface for Git repositories` | Subtitle under the title. |
| `CGIT_LOGO` | `/cgit.png` | Logo image path or URL. |
| `CGIT_LOGO_LINK` | `/` | Target URL when clicking the logo. |
| `CGIT_CLONE_PREFIX` | *unset* | Base URL prefix shown for `git clone` links (e.g. `https://git.example.com`). |
| `CGIT_ENABLE_HTTP_CLONE` | `1` | Enable HTTP `git clone` via `git-http-backend` (`1` or `0`). |
| `CGIT_ENABLE_SYNTAX_HIGHLIGHT` | `1` | Enable server-side syntax highlighting via `highlight` (`1` or `0`). |
| `CGIT_SIDE_BY_SIDE_DIFFS` | `0` | Use side-by-side diffs by default (`1` or `0`). |
| `CGIT_MAX_STATS` | `quarter` | Maximum stats period (`week`, `month`, `quarter`, `year`). |
| `CGIT_CACHE_SIZE` | `1000` | Number of cached page entries (`0` to disable). |
| `CGIT_PORT` | `80` | HTTP listening port inside the container. |
| `CGIT_EXTRA_CONFIG` | *unset* | Extra raw `cgitrc` lines appended before `scan-path`. |
