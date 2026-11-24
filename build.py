#!/usr/bin/env python3
"""
Multi-Architecture Docker Image Build & Cloud-Sync Wizard

Features:
  1. Tier 1: Cloud-to-Cloud Direct Sync (0 build, ~5 seconds)
     Detects official pre-built multi-arch images on GHCR (with preference
     for minimal variants: alpine, slim). Directly re-tags and pushes
     multi-arch manifests (linux/amd64 + linux/arm64) to Docker Hub via imagetools.
  2. Tier 2: Hybrid Assemble (Stitch single-arch + native build)
     If GHCR provides only amd64, Mac Apple Silicon builds arm64 natively
     (no QEMU), then stitches them into a unified multi-arch manifest.
  3. Tier 3: Full Fallback Build
     If no pre-built image exists, automatically clones source and builds
     multi-platform images using Docker Buildx.
  4. Automatic Skip: Checks Docker Hub first; skips if version is already published.
"""

import argparse
import glob
import json
import os
import platform
import re
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request

# --- Terminal Styling ---
class Colors:
    GREEN = "\033[92m"
    BLUE = "\033[94m"
    CYAN = "\033[96m"
    YELLOW = "\033[93m"
    RED = "\033[91m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    RESET = "\033[0m"

    @classmethod
    def disable(cls):
        cls.GREEN = cls.BLUE = cls.CYAN = cls.YELLOW = cls.RED = cls.BOLD = cls.DIM = cls.RESET = ""

if not sys.stdout.isatty() or (os.name == "nt" and "WT_SESSION" not in os.environ and "TERM" not in os.environ):
    Colors.disable()


def log_info(msg):
    print(f"{Colors.BLUE}[INFO]{Colors.RESET} {msg}")

def log_success(msg):
    print(f"{Colors.GREEN}[SUCCESS]{Colors.RESET} {msg}")

def log_warn(msg):
    print(f"{Colors.YELLOW}[WARN]{Colors.RESET} {msg}")

def log_error(msg):
    print(f"{Colors.RED}[ERROR]{Colors.RESET} {msg}")

def log_step(msg):
    print(f"\n{Colors.BOLD}{Colors.CYAN}==> {msg}{Colors.RESET}")


def safe_input(prompt=""):
    """Prompt user for input, exiting cleanly on Ctrl+C or EOF."""
    try:
        return input(prompt)
    except (EOFError, KeyboardInterrupt):
        print("\nAborted.")
        sys.exit(0)


def get_docker_cmd():
    """Detect docker and buildx availability."""
    docker_bin = shutil.which("docker")
    if not docker_bin:
        log_error("Docker is not installed or not found in PATH.")
        sys.exit(1)

    buildx_prefix = [docker_bin, "buildx"]
    try:
        subprocess.run(buildx_prefix + ["version"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
    except Exception:
        alt_buildx = shutil.which("docker-buildx")
        if alt_buildx:
            buildx_prefix = [alt_buildx]
        else:
            log_error("Docker Buildx plugin not found.")
            sys.exit(1)

    return docker_bin, buildx_prefix


def load_env_file():
    """Load key-value pairs from .env."""
    env_vars = {}
    env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
    if os.path.exists(env_path):
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    env_vars[k.strip()] = v.strip().strip("'\"")
    return env_vars


def get_dockerhub_username():
    """Get Docker Hub username from environment, .env, or prompt."""
    username = os.environ.get("DOCKERHUB_USERNAME")
    if username:
        return username

    env_vars = load_env_file()
    if env_vars.get("DOCKERHUB_USERNAME"):
        return env_vars["DOCKERHUB_USERNAME"]

    default_user = "tozp"
    print(f"{Colors.YELLOW}[?] Docker Hub username not set in environment.{Colors.RESET}")
    user_input = safe_input(f"Enter Docker Hub username/namespace [default: {default_user}]: ").strip()
    username = user_input if user_input else default_user

    save_env = safe_input(f"Save DOCKERHUB_USERNAME={username} to .env? [Y/n]: ").strip().lower()
    if save_env in ("", "y", "yes"):
        env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
        with open(env_path, "a", encoding="utf-8") as f:
            f.write(f"\nDOCKERHUB_USERNAME={username}\n")
        log_success(f"Saved DOCKERHUB_USERNAME={username} to .env")

    return username


def parse_build_yml(config_path):
    """Parse project build.yml without external YAML dependency."""
    with open(config_path, "r", encoding="utf-8") as f:
        content = f.read()

    up_m = re.search(r"^x-upstream:\s*(.+)$", content, re.M)
    upstream = up_m.group(1).strip() if up_m else None

    ghcr_m = re.search(r"^x-ghcr-image:\s*(.+)$", content, re.M)
    explicit_ghcr = ghcr_m.group(1).strip() if ghcr_m else None

    var_m = re.search(r"^x-variant-preference:\s*(.+)$", content, re.M)
    variant_pref = var_m.group(1).strip() if var_m else None

    project_id = os.path.basename(os.path.dirname(config_path))

    img_m = re.search(r"image:\s*\$\{DOCKERHUB_USERNAME[^}]*\}\/([a-zA-Z0-9_.-]+):", content)
    repo_name = img_m.group(1).strip() if img_m else project_id

    df_m = re.search(r"dockerfile:\s*(.+)$", content, re.M)
    dockerfile = df_m.group(1).strip() if df_m else "Dockerfile"

    target_m = re.search(r"target:\s*(.+)$", content, re.M)
    target = target_m.group(1).strip() if target_m else None

    platforms = re.findall(r"-\s*(linux/[a-zA-Z0-9_/]+)", content)
    if not platforms:
        platforms = ["linux/amd64", "linux/arm64"]

    return {
        "project_id": project_id,
        "config_path": config_path,
        "upstream": upstream,
        "explicit_ghcr": explicit_ghcr,
        "variant_preference": variant_pref,
        "repo_name": repo_name,
        "dockerfile": dockerfile,
        "target": target,
        "platforms": platforms,
    }


def discover_projects():
    """Discover all active project configs under images/*/build.yml."""
    configs = sorted(glob.glob("images/*/build.yml"))
    projects = []
    for c in configs:
        parsed = parse_build_yml(c)
        if parsed["upstream"]:
            projects.append(parsed)
    return projects


def fetch_upstream_latest_version(upstream):
    """Query GitHub API for latest release or tag."""
    headers = {
        "User-Agent": "Docker-Build-Wizard/1.0",
        "Accept": "application/vnd.github.v3+json",
    }
    github_token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if github_token:
        headers["Authorization"] = f"Bearer {github_token}"

    for endpoint in ["releases/latest", "releases", "tags"]:
        url = f"https://api.github.com/repos/{upstream}/{endpoint}"
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode())
                if isinstance(data, dict) and data.get("tag_name"):
                    return data["tag_name"]
                elif isinstance(data, list) and len(data) > 0:
                    tag = data[0].get("tag_name") or data[0].get("name")
                    if tag:
                        return tag
        except Exception:
            continue

    raise RuntimeError(f"No releases or tags found for {upstream}")


def normalize_version(tag):
    """Strip leading prefixes (e.g. 'v1.7.4' -> '1.7.4')."""
    m = re.search(r"(\d+(\.\d+)*(-[a-zA-Z0-9_.-]+)?)", tag)
    return m.group(1) if m else tag.lstrip("v")


def is_already_published_on_dockerhub(target_repo, version, required_platforms):
    """
    Check Docker Hub API to see if target_repo:version already contains
    all required platforms (e.g. linux/amd64 and linux/arm64).
    """
    url = f"https://hub.docker.com/v2/repositories/{target_repo}/tags/{version}"
    headers = {"User-Agent": "Docker-Build-Wizard/1.0"}
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=8) as resp:
            data = json.loads(resp.read().decode())
            images = data.get("images", [])
            existing_platforms = {
                f"{img.get('os')}/{img.get('architecture')}"
                for img in images if img.get("os") and img.get("architecture")
            }
            return all(p in existing_platforms for p in required_platforms)
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return False
    except Exception:
        pass
    return False


def get_candidate_ghcr_repositories(project):
    """Return candidate GHCR repositories for a project."""
    candidates = []
    if project.get("explicit_ghcr"):
        candidates.append(project["explicit_ghcr"])

    upstream = project["upstream"]
    owner, repo = upstream.split("/", 1)
    project_id = project["project_id"]

    candidates.append(f"ghcr.io/{owner.lower()}/{repo.lower()}")
    if project_id.lower() != repo.lower():
        candidates.append(f"ghcr.io/{owner.lower()}/{project_id.lower()}")

    # Deduplicate preserving order
    seen = set()
    return [c for c in candidates if not (c in seen or seen.add(c))]


def get_variant_candidate_tags(version, variant_pref=None):
    """Generate candidate tags in priority order with minimal variants first."""
    v = version.lstrip("v")
    tags = []

    if variant_pref == "slim":
        tags.extend([f"{v}-slim", f"v{v}-slim", f"{v}", f"v{v}"])
    elif variant_pref == "alpine":
        tags.extend([f"{v}-alpine", f"v{v}-alpine", f"{v}", f"v{v}"])
    else:
        tags.extend([
            f"{v}-alpine", f"v{v}-alpine",
            f"{v}-slim", f"v{v}-slim",
            f"{v}", f"v{v}", f"{version}",
        ])

    seen = set()
    return [t for t in tags if not (t in seen or seen.add(t))]


def probe_ghcr_image(buildx_prefix, ghcr_repo, tag):
    """Check if a GHCR image tag exists and parse its platforms."""
    inspect_cmd = buildx_prefix + ["imagetools", "inspect", "--raw", f"{ghcr_repo}:{tag}"]
    try:
        res = subprocess.run(inspect_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        if res.returncode != 0:
            return False, []

        manifest_raw = res.stdout.strip()
        data = json.loads(manifest_raw)

        platforms = []
        if "manifests" in data:
            for m in data.get("manifests", []):
                p = m.get("platform", {})
                os_name = p.get("os", "")
                arch = p.get("architecture", "")
                if os_name and arch:
                    platforms.append(f"{os_name}/{arch}")
        elif "architecture" in data:
            platforms.append(f"{data.get('os', 'linux')}/{data.get('architecture')}")
        else:
            platforms.append("linux/amd64")

        return True, platforms
    except Exception:
        return False, []


def find_ghcr_image(buildx_prefix, project, version):
    """Search GHCR for suitable pre-built image with minimal variant preference."""
    candidate_repos = get_candidate_ghcr_repositories(project)
    candidate_tags = get_variant_candidate_tags(version, project.get("variant_preference"))

    log_info("Probing GHCR for pre-built images (preferring minimal variants)...")
    for repo in candidate_repos:
        for tag in candidate_tags:
            full_ref = f"{repo}:{tag}"
            print(f"  {Colors.DIM}Checking {full_ref}...{Colors.RESET}", end="\r", flush=True)
            exists, platforms = probe_ghcr_image(buildx_prefix, repo, tag)
            if exists:
                print(" " * 80, end="\r")
                variant = "standard"
                if "slim" in tag.lower():
                    variant = "slim"
                elif "alpine" in tag.lower():
                    variant = "alpine"
                elif "minimal" in tag.lower():
                    variant = "minimal"

                log_success(f"Found on GHCR: {Colors.BOLD}{full_ref}{Colors.RESET} [{variant}]")
                log_info(f"Available platforms: {', '.join(platforms)}")
                return full_ref, variant, platforms

    print(" " * 80, end="\r")
    return None


def sync_direct_imagetools(buildx_prefix, source_ref, target_repo, version, variant):
    """Tier 1: Cloud-to-Cloud sync multi-arch index directly to Docker Hub."""
    target_tags = [f"{target_repo}:{version}", f"{target_repo}:latest"]

    # If it's a slim or alpine variant, publish both standard and variant tags
    if variant in ("slim", "alpine"):
        target_tags.append(f"{target_repo}:{variant}")
        target_tags.append(f"{target_repo}:{version}-{variant}")
        target_tags.append(f"{target_repo}:latest-{variant}")

    log_step(f"[Tier 1: Cloud Direct Sync] {source_ref} -> {target_repo}")
    cmd = buildx_prefix + ["imagetools", "create"]
    for t in target_tags:
        cmd.extend(["--tag", t])
    cmd.append(source_ref)

    log_info(f"Executing: {' '.join(cmd)}")
    subprocess.run(cmd, check=True)
    log_success("Successfully synced multi-arch image to Docker Hub:")
    for t in target_tags:
        print(f"  {Colors.GREEN}✔ {t}{Colors.RESET}")


def ensure_buildx_builder(buildx_prefix):
    """Ensure a container-based buildx builder instance is available."""
    try:
        ls_res = subprocess.run(buildx_prefix + ["ls"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True)
        for line in ls_res.stdout.splitlines():
            if "*" in line and "docker-container" in line:
                return
    except Exception:
        pass

    builder_name = "multiarch-builder"
    log_info(f"Creating container-based Buildx builder ('{builder_name}')...")
    try:
        subprocess.run(buildx_prefix + ["create", "--name", builder_name, "--driver", "docker-container", "--use"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
        subprocess.run(buildx_prefix + ["inspect", "--bootstrap"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
    except Exception as e:
        log_warn(f"Builder setup note: {e}")


def hybrid_assemble_build(buildx_prefix, project, git_tag, version, target_repo, ghcr_ref, existing_platforms, missing_platforms, variant):
    """
    Tier 2: Build ONLY the missing platform natively, then stitch with GHCR.
    Example: GHCR has linux/amd64; on Apple Silicon (arm64), build only linux/arm64
    natively (fast!), then combine both with imagetools create.
    """
    log_step(f"[Tier 2: Hybrid Assemble] Missing: {missing_platforms}, Sourcing: {existing_platforms}")
    ensure_buildx_builder(buildx_prefix)

    upstream = project["upstream"]
    missing_str = ",".join(missing_platforms)
    temp_single_tag = f"{target_repo}:{version}-temp-{missing_platforms[0].replace('/', '-')}"

    with tempfile.TemporaryDirectory(prefix="docker-hybrid-") as tmpdir:
        clone_url = f"https://github.com/{upstream}.git"
        log_info(f"Cloning {clone_url} at {git_tag}...")
        subprocess.run(["git", "clone", "--depth", "1", "--branch", git_tag, clone_url, tmpdir], check=True)

        # Apply project overrides
        custom_dockerfile = os.path.join(os.path.dirname(project["config_path"]), "Dockerfile")
        if os.path.exists(custom_dockerfile):
            shutil.copy(custom_dockerfile, os.path.join(tmpdir, project["dockerfile"]))

        if project["project_id"] == "deer-flow-frontend":
            env_file = os.path.join(tmpdir, "frontend", ".env.production.local")
            os.makedirs(os.path.dirname(env_file), exist_ok=True)
            with open(env_file, "w") as f:
                f.write("DEER_FLOW_INTERNAL_GATEWAY_BASE_URL=http://deer-flow-gateway:8001\n")

        build_cmd = buildx_prefix + [
            "build",
            "--platform", missing_str,
            "-t", temp_single_tag,
            "-f", os.path.join(tmpdir, project["dockerfile"]),
        ]
        if project.get("target"):
            build_cmd.extend(["--target", project["target"]])
        build_cmd.extend(["--push", tmpdir])

        log_info(f"Building ONLY missing platform ({missing_str}) natively...")
        subprocess.run(build_cmd, check=True)

        # Stitch existing GHCR image + newly built single-arch image
        target_tags = [f"{target_repo}:{version}", f"{target_repo}:latest"]
        if variant in ("slim", "alpine"):
            target_tags.extend([f"{target_repo}:{variant}", f"{target_repo}:{version}-{variant}"])

        stitch_cmd = buildx_prefix + ["imagetools", "create"]
        for t in target_tags:
            stitch_cmd.extend(["--tag", t])
        stitch_cmd.extend([ghcr_ref, temp_single_tag])

        log_info(f"Stitching {ghcr_ref} + {temp_single_tag} -> Docker Hub...")
        subprocess.run(stitch_cmd, check=True)

        log_success("Successfully assembled and published multi-arch image:")
        for t in target_tags:
            print(f"  {Colors.GREEN}✔ {t}{Colors.RESET}")


def full_fallback_build(buildx_prefix, project, git_tag, version, target_repo):
    """Tier 3: Build both platforms from source via Docker Buildx."""
    log_step(f"[Tier 3: Full Build Fallback] Building {project['project_id']} from source")
    ensure_buildx_builder(buildx_prefix)

    upstream = project["upstream"]
    platforms_str = ",".join(project["platforms"])
    target_v = f"{target_repo}:{version}"
    target_latest = f"{target_repo}:latest"

    with tempfile.TemporaryDirectory(prefix="docker-build-") as tmpdir:
        clone_url = f"https://github.com/{upstream}.git"
        log_info(f"Cloning {clone_url} at {git_tag}...")
        subprocess.run(["git", "clone", "--depth", "1", "--branch", git_tag, clone_url, tmpdir], check=True)

        custom_dockerfile = os.path.join(os.path.dirname(project["config_path"]), "Dockerfile")
        if os.path.exists(custom_dockerfile):
            shutil.copy(custom_dockerfile, os.path.join(tmpdir, project["dockerfile"]))

        if project["project_id"] == "deer-flow-frontend":
            env_file = os.path.join(tmpdir, "frontend", ".env.production.local")
            os.makedirs(os.path.dirname(env_file), exist_ok=True)
            with open(env_file, "w") as f:
                f.write("DEER_FLOW_INTERNAL_GATEWAY_BASE_URL=http://deer-flow-gateway:8001\n")

        build_cmd = buildx_prefix + [
            "build",
            "--platform", platforms_str,
            "-t", target_v,
            "-t", target_latest,
            "-f", os.path.join(tmpdir, project["dockerfile"]),
        ]
        if project.get("target"):
            build_cmd.extend(["--target", project["target"]])
        build_cmd.extend(["--push", tmpdir])

        log_info(f"Building for {platforms_str}...")
        subprocess.run(build_cmd, check=True)

        log_success("Build complete and published to Docker Hub:")
        print(f"  {Colors.GREEN}✔ {target_v}{Colors.RESET}")
        print(f"  {Colors.GREEN}✔ {target_latest}{Colors.RESET}")


def process_project(buildx_prefix, project, dockerhub_user, target_version=None, auto_confirm=False, force=False):
    """Orchestrate 3-tier build/sync pipeline for a single project."""
    project_id = project["project_id"]
    upstream = project["upstream"]
    target_repo = f"{dockerhub_user}/{project['repo_name']}"
    required_platforms = set(project["platforms"])

    print("\n" + "=" * 65)
    print(f" {Colors.BOLD}Project:{Colors.RESET}      {project_id}")
    print(f" {Colors.BOLD}Upstream:{Colors.RESET}     https://github.com/{upstream}")
    print(f" {Colors.BOLD}Target Hub:{Colors.RESET}   {target_repo}")
    print(f" {Colors.BOLD}Platforms:{Colors.RESET}    {', '.join(project['platforms'])}")
    print("=" * 65)

    # 1. Version resolution
    if not target_version:
        log_info(f"Querying GitHub for latest release of {upstream}...")
        try:
            git_tag = fetch_upstream_latest_version(upstream)
            detected_version = normalize_version(git_tag)
        except Exception as e:
            log_error(f"Failed to query upstream release: {e}")
            git_tag = safe_input("Enter upstream git tag (e.g. v1.0.0): ").strip()
            detected_version = normalize_version(git_tag)

        print(f"\n{Colors.BOLD}Latest Upstream Tag:{Colors.RESET} {Colors.CYAN}{git_tag}{Colors.RESET} -> Version: {Colors.GREEN}{detected_version}{Colors.RESET}")

        if not auto_confirm:
            confirm = safe_input(f"Proceed with version '{detected_version}'? [Y/n/custom]: ").strip()
            if confirm.lower() in ("n", "no"):
                log_warn(f"Skipping {project_id}.")
                return
            elif confirm and confirm.lower() not in ("y", "yes"):
                detected_version = confirm.strip()
                git_tag = detected_version if detected_version.startswith("v") else f"v{detected_version}"
        version = detected_version
    else:
        version = normalize_version(target_version)
        git_tag = target_version if target_version.startswith("v") else f"v{version}"

    # 2. Skip check: already on Docker Hub?
    if not force:
        if is_already_published_on_dockerhub(target_repo, version, required_platforms):
            log_success(f"{target_repo}:{version} is already published on Docker Hub with all platforms ({', '.join(required_platforms)}). Skipping!")
            return

    start_time = time.time()

    # 3. Check GHCR (Tier 1 & Tier 2)
    ghcr_result = find_ghcr_image(buildx_prefix, project, version)
    if ghcr_result:
        source_ref, variant, available_platforms = ghcr_result
        available_set = set(available_platforms)

        # Check if all required platforms exist in GHCR
        if required_platforms.issubset(available_set):
            # Tier 1: Complete Cloud Sync
            try:
                sync_direct_imagetools(buildx_prefix, source_ref, target_repo, version, variant)
                elapsed = time.time() - start_time
                log_success(f"Finished {project_id} in {elapsed:.1f}s via Tier 1 Cloud Direct Sync!")
                return
            except Exception as e:
                log_warn(f"Tier 1 sync failed ({e}). Proceeding to assemble/build...")
        else:
            # Tier 2: Hybrid Assemble
            missing = list(required_platforms - available_set)
            log_info(f"GHCR image lacks: {missing}. Available: {available_platforms}.")
            try:
                hybrid_assemble_build(buildx_prefix, project, git_tag, version, target_repo, source_ref, available_platforms, missing, variant)
                elapsed = time.time() - start_time
                log_success(f"Finished {project_id} in {elapsed:.1f}s via Tier 2 Hybrid Assemble!")
                return
            except Exception as e:
                log_warn(f"Tier 2 hybrid assemble failed ({e}). Falling back to full build...")

    # 4. Tier 3: Full Fallback Build
    log_info("Executing Tier 3: Full multi-arch build from source...")
    try:
        full_fallback_build(buildx_prefix, project, git_tag, version, target_repo)
        elapsed = time.time() - start_time
        log_success(f"Finished {project_id} in {elapsed:.1f}s via Tier 3 Docker Buildx!")
    except Exception as e:
        log_error(f"Build failed for {project_id}: {e}")
        raise e


def interactive_wizard():
    """Interactive wizard menu."""
    print(f"""
{Colors.CYAN}{Colors.BOLD}==============================================================
          🚀 Docker Multi-Arch Build & Fast-Sync Wizard
=============================================================={Colors.RESET}
  * Tier 1: Direct Cloud Sync (0 build, 5s)
  * Tier 2: Hybrid Assemble (build missing arch natively)
  * Tier 3: Full Buildx Fallback (from source)
""")

    _, buildx_prefix = get_docker_cmd()
    dockerhub_user = get_dockerhub_username()
    projects = discover_projects()

    if not projects:
        log_error("No project build configurations found under images/*/build.yml.")
        sys.exit(1)

    while True:
        print(f"\n{Colors.BOLD}Available Projects:{Colors.RESET}")
        for idx, p in enumerate(projects, start=1):
            var_hint = f" [{p['variant_preference']}]" if p.get("variant_preference") else ""
            print(f"  [{Colors.CYAN}{idx}{Colors.RESET}] {p['project_id']:<22}{var_hint} (Upstream: {p['upstream']})")
        print("  " + "-" * 55)
        print(f"  [{Colors.YELLOW}A{Colors.RESET}] Build / Sync All Projects")
        print(f"  [{Colors.RED}Q{Colors.RESET}] Quit")
        print("-" * 62)

        choice = safe_input(f"Select a project [1-{len(projects)}/A/Q]: ").strip()
        if not choice:
            continue

        if choice.upper() == "Q":
            print("Exiting. Bye!")
            break

        if choice.upper() == "A":
            confirm = safe_input("Process ALL projects? [y/N]: ").strip().lower()
            if confirm in ("y", "yes"):
                for p in projects:
                    try:
                        process_project(buildx_prefix, p, dockerhub_user)
                    except Exception as e:
                        log_error(f"Error on {p['project_id']}: {e}")
            continue

        if choice.isdigit() and 1 <= int(choice) <= len(projects):
            selected_project = projects[int(choice) - 1]
            try:
                process_project(buildx_prefix, selected_project, dockerhub_user)
            except Exception as e:
                log_error(f"Error: {e}")

            cont = safe_input(f"\n{Colors.BOLD}Process another project? [Y/n]: {Colors.RESET}").strip().lower()
            if cont in ("n", "no"):
                print("Done! Exiting.")
                break
        else:
            log_warn("Invalid selection. Please try again.")


def main():
    parser = argparse.ArgumentParser(description="Multi-arch Docker Image Builder and Cloud Fast-Sync")
    parser.add_argument("project", nargs="?", help="Project ID under images/ (or 'all')")
    parser.add_argument("--tag", "-t", help="Specific upstream version/tag")
    parser.add_argument("--yes", "-y", action="store_true", help="Auto-confirm all prompts")
    parser.add_argument("--force", "-f", action="store_true", help="Force rebuild even if already published")
    parser.add_argument("--user", "-u", help="Docker Hub username override")
    args = parser.parse_args()

    if not args.project:
        interactive_wizard()
        return

    _, buildx_prefix = get_docker_cmd()
    dockerhub_user = args.user or get_dockerhub_username()
    projects = {p["project_id"]: p for p in discover_projects()}

    if args.project == "all":
        for p in projects.values():
            process_project(buildx_prefix, p, dockerhub_user, target_version=args.tag, auto_confirm=args.yes, force=args.force)
    elif args.project in projects:
        process_project(buildx_prefix, projects[args.project], dockerhub_user, target_version=args.tag, auto_confirm=args.yes, force=args.force)
    else:
        log_error(f"Project '{args.project}' not found. Available: {', '.join(projects.keys())}")
        sys.exit(1)


if __name__ == "__main__":
    main()
