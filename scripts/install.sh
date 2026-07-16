#!/usr/bin/env bash
set -euo pipefail

# One-shot native and Docker installer for DevLog.
# Usage:
#   curl -fsSL https://raw.githubusercontent.com/dbowm91/blog/main/scripts/install.sh | bash -s -- --native
#   curl -fsSL https://raw.githubusercontent.com/dbowm91/blog/main/scripts/install.sh | bash -s -- --docker
#   curl -fsSL https://raw.githubusercontent.com/dbowm91/blog/main/scripts/install.sh | bash -s -- --native --user

# ── Constants ──────────────────────────────────────────────────────────────────

readonly REPO="dbowm91/blog"
readonly REPO_URL="https://github.com/${REPO}"
readonly RELEASES_URL="${REPO_URL}/releases/download"
readonly API_URL="https://api.github.com/repos/${REPO}/releases"
readonly WHEEL_PATTERN="devlog-%s-py3-none-any.whl"
readonly DOCKER_BUNDLE_PATTERN="docker-bundle-%s.tar.gz"
readonly CHECKSUMS_FILE="checksums.txt"

# ── Global state ───────────────────────────────────────────────────────────────

INSTALL_MODE=""
INSTALL_SCOPE=""
TARGET_VERSION=""
CHANNEL="stable"
PREFIX=""
DRY_RUN=false
NON_INTERACTIVE=false
YES=false
NO_ONBOARD=false
RUN_ONBOARD=false
BACKEND=""
OS_NAME=""
ARCH_NAME=""
ARTIFACTS_DIR=""
RELEASE_DIR=""
PREV_CURRENT=""
TEMP_DIR=""
FAILURE_STAGE=""
INSTALLED_VERSION=""

# ── Logging ────────────────────────────────────────────────────────────────────

log()   { printf '%s\n' "$*" >&2; }
info()  { printf '\033[34m==>\033[0m %s\n' "$*" >&2; }
ok()    { printf '\033[32m  ✓\033[0m %s\n' "$*" >&2; }
warn()  { printf '\033[33m  ⚠\033[0m %s\n' "$*" >&2; }
fail()  { printf '\033[31m  ✗\033[0m %s\n' "$*" >&2; }
die()   { fail "$1"; exit "${2:-1}"; }

# ── Cleanup and error trap ─────────────────────────────────────────────────────

cleanup() {
    local exit_code=$?
    if [ "$exit_code" -ne 0 ] && [ -n "$FAILURE_STAGE" ]; then
        echo "" >&2
        fail "Installation failed at: ${FAILURE_STAGE}"
        if [ "$INSTALL_MODE" = "native" ] && [ -n "$TEMP_DIR" ] && [ -d "$TEMP_DIR" ]; then
            info "Cleaning up temporary files..."
            rm -rf "$TEMP_DIR"
        fi
        if [ "$INSTALL_MODE" = "native" ] && [ -n "$PREV_CURRENT" ]; then
            if [ -L "${PREFIX}/current" ]; then
                info "Previous installation preserved — no changes were made."
            fi
        fi
        echo "" >&2
        echo "For help: https://github.com/${REPO}/issues" >&2
    fi
}

trap cleanup EXIT

# ── Helpers ────────────────────────────────────────────────────────────────────

require_cmd() {
    command -v "$1" >/dev/null 2>&1 || die "$2"
}

version_gte() {
    printf '%s\n%s' "$2" "$1" | sort -V -C
}

portable_sha256() {
    if command -v sha256sum >/dev/null 2>&1; then
        sha256sum "$1" | cut -d' ' -f1
    elif command -v shasum >/dev/null 2>&1; then
        shasum -a 256 "$1" | cut -d' ' -f1
    else
        die "No SHA-256 tool found. Install coreutils (sha256sum) or Perl (shasum)."
    fi
}

extract_version() {
    local version_str
    version_str="$("$1" --version 2>&1 | head -1)" || true
    version_str="$(printf '%s' "$version_str" | sed -E 's/[^0-9]*([0-9]+\.[0-9]+\.[0-9]+[a-zA-Z0-9._-]*).*/\1/')" || true
    printf '%s' "$version_str"
}

atomic_move() {
    local src="$1" dst="$2"
    if mv -Tf "$src" "$dst" 2>/dev/null; then
        return 0
    fi
    rm -f "$dst"
    mv "$src" "$dst"
}

detect_os() {
    local os_type
    os_type="$(uname -s)"
    case "$os_type" in
        Linux*)  OS_NAME="linux" ;;
        Darwin*) OS_NAME="macos" ;;
        *)       die "Unsupported operating system: $os_type" ;;
    esac
}

detect_arch() {
    local arch_type
    arch_type="$(uname -m)"
    case "$arch_type" in
        x86_64|amd64)  ARCH_NAME="amd64" ;;
        aarch64|arm64) ARCH_NAME="arm64" ;;
        armv7l|armhf)  ARCH_NAME="arm" ;;
        *)             die "Unsupported architecture: $arch_type" ;;
    esac
}

# ── Phase 1: Parse options ─────────────────────────────────────────────────────

parse_options() {
    while [ $# -gt 0 ]; do
        case "$1" in
            --native)         INSTALL_MODE="native"; shift ;;
            --docker)         INSTALL_MODE="docker"; shift ;;
            --user)           INSTALL_SCOPE="user"; shift ;;
            --system)         INSTALL_SCOPE="system"; shift ;;
            --version)
                [ $# -ge 2 ] || die "Option --version requires a value"
                TARGET_VERSION="$2"; shift 2 ;;
            --prefix)
                [ $# -ge 2 ] || die "Option --prefix requires a value"
                PREFIX="$2"; shift 2 ;;
            --channel)
                [ $# -ge 2 ] || die "Option --channel requires a value"
                case "$2" in
                    stable|prerelease) CHANNEL="$2" ;;
                    *) die "Invalid channel: $2 (must be stable or prerelease)" ;;
                esac
                shift 2 ;;
            --non-interactive) NON_INTERACTIVE=true; shift ;;
            --dry-run)         DRY_RUN=true; shift ;;
            --yes|-y)          YES=true; shift ;;
            --no-onboard)      NO_ONBOARD=true; shift ;;
            --onboard)         RUN_ONBOARD=true; shift ;;
            --help|-h)         usage; exit 0 ;;
            *) die "Unknown option: $1 (use --help for usage)" ;;
        esac
    done

    if [ -z "$INSTALL_MODE" ]; then
        INSTALL_MODE="native"
    fi

    if [ -z "$INSTALL_SCOPE" ]; then
        INSTALL_SCOPE="system"
    fi

    if [ -z "$PREFIX" ]; then
        if [ "$INSTALL_SCOPE" = "user" ]; then
            PREFIX="${XDG_LOCAL_HOME:-${HOME}/.local}"
        else
            PREFIX="/opt/devlog"
        fi
    fi
}

usage() {
    cat >&2 <<'EOF'
DevLog Installer — one-shot native and Docker installation

Usage:
  install.sh [OPTIONS]

Modes:
  --native          Native installation (default)
  --docker          Docker Compose bundle installation

Scope (native only):
  --system          Install to system paths (default: /opt/devlog)
  --user            Install to user paths (~/.local/share/devlog)

Version and channel:
  --version VER     Install a specific version (e.g. 1.0.0)
  --channel CHANNEL Release channel: stable (default) or prerelease

Paths (native only):
  --prefix PATH     Installation prefix

Behavior:
  --non-interactive  Disable interactive prompts
  --yes, -y          Accept all confirmations
  --dry-run          Show what would be done without changes
  --no-onboard       Skip onboarding after install
  --onboard          Run onboarding immediately (requires TTY)

Examples:
  curl -fsSL https://raw.githubusercontent.com/dbowm91/blog/main/scripts/install.sh | bash -s -- --native
  curl -fsSL ... | bash -s -- --native --user --version 1.2.0
  curl -fsSL ... | bash -s -- --docker
  install.sh --native --onboard
EOF
}

# ── Phase 2: Detect OS/architecture ────────────────────────────────────────────

detect_platform() {
    info "Detecting platform..."
    detect_os
    detect_arch
    ok "Platform: ${OS_NAME}/${ARCH_NAME}"
}

# ── Phase 3: Select backend ────────────────────────────────────────────────────

select_backend() {
    if [ "$INSTALL_MODE" = "docker" ]; then
        BACKEND="docker"
        return
    fi

    if command -v python3 >/dev/null 2>&1; then
        BACKEND="venv"
    else
        die "Python 3 is required for native installation but was not found."
    fi
}

# ── Phase 4: Check prerequisites ───────────────────────────────────────────────

check_native_prereqs() {
    info "Checking prerequisites..."

    require_cmd python3 "Python 3 is required but not found. Install Python 3.12+."

    local py_version
    py_version="$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')"
    local py_major py_minor
    py_major="$(echo "$py_version" | cut -d. -f1)"
    py_minor="$(echo "$py_version" | cut -d. -f2)"

    if [ "$py_major" -lt 3 ] || { [ "$py_major" -eq 3 ] && [ "$py_minor" -lt 12 ]; }; then
        die "Python 3.12+ is required. Found: Python ${py_version}"
    fi
    ok "Python ${py_version}"

    python3 -c "import venv" 2>/dev/null || die "Python venv module is required but not available."
    ok "venv module available"

    if python3 -c "import sqlite3; conn = sqlite3.connect(':memory:'); conn.execute('CREATE VIRTUAL TABLE IF NOT EXISTS _test USING fts5(content)'); conn.close()" 2>/dev/null; then
        ok "SQLite FTS5 available"
    else
        warn "SQLite FTS5 not available — search will use LIKE fallback"
    fi

    require_cmd curl "curl is required for downloading artifacts."
    ok "curl available"

    if [ "$OS_NAME" = "linux" ]; then
        if [ -f /etc/ssl/certs/ca-certificates.crt ] || [ -d /etc/ssl/certs ]; then
            ok "CA certificates found"
        elif command -v update-ca-certificates >/dev/null 2>&1; then
            warn "CA certificates not found. You may need: sudo update-ca-certificates"
        else
            warn "Could not verify CA certificates. HTTPS downloads may fail."
        fi
    fi

    if [ "$INSTALL_SCOPE" = "system" ]; then
        if [ -w "$(dirname "$PREFIX")" ] 2>/dev/null; then
            ok "Writable: $(dirname "$PREFIX")"
        else
            if [ "$(id -u)" -ne 0 ]; then
                warn "System installation requires sudo for: $(dirname "$PREFIX")"
                if [ "$NON_INTERACTIVE" = false ] && [ "$YES" = false ]; then
                    printf '\033[33mContinue with sudo? [y/N] \033[0m' >&2
                    read -r answer </dev/tty || answer="n"
                    case "$answer" in
                        [yY]|[yY][eE][sS]) ;;
                        *) die "Installation cancelled." ;;
                    esac
                fi
            fi
        fi
    fi

    ok "Prerequisites satisfied"
}

check_docker_prereqs() {
    info "Checking Docker prerequisites..."

    require_cmd docker "Docker Engine is required for Docker mode. Install Docker: https://docs.docker.com/get-docker/"

    if ! docker info >/dev/null 2>&1; then
        die "Docker daemon is not running or current user lacks permission. Start Docker or add user to docker group."
    fi
    ok "Docker Engine running"

    if docker compose version >/dev/null 2>&1; then
        ok "Docker Compose plugin available"
    elif command -v docker-compose >/dev/null 2>&1; then
        ok "docker-compose (standalone) available"
    else
        die "Docker Compose plugin is required. Install: https://docs.docker.com/compose/install/"
    fi
}

# ── Phase 5: Resolve version ───────────────────────────────────────────────────

resolve_version() {
    if [ -n "$TARGET_VERSION" ]; then
        TARGET_VERSION="${TARGET_VERSION#v}"
        info "Target version: ${TARGET_VERSION}"
        return
    fi

    info "Resolving latest ${CHANNEL} version..."

    local api_url
    if [ "$CHANNEL" = "stable" ]; then
        api_url="${API_URL}/latest"
    else
        api_url="${API_URL}?per_page=10"
    fi

    local api_response
    api_response="$(curl -fsSL \
        -H "Accept: application/vnd.github.v3+json" \
        "$api_url" 2>/dev/null)" || die "Failed to query GitHub API. Check network connectivity."

    if [ "$CHANNEL" = "stable" ]; then
        TARGET_VERSION="$(echo "$api_response" | python3 -c '
import sys, json
data = json.load(sys.stdin)
tag = data.get("tag_name", "")
print(tag.lstrip("v"))
' 2>/dev/null)" || true
    else
        TARGET_VERSION="$(echo "$api_response" | python3 -c '
import sys, json
data = json.load(sys.stdin)
if isinstance(data, list):
    for release in data:
        if release.get("prerelease", False):
            tag = release.get("tag_name", "")
            print(tag.lstrip("v"))
            sys.exit(0)
print("")
' 2>/dev/null)" || true
    fi

    if [ -z "$TARGET_VERSION" ]; then
        die "Could not determine latest ${CHANNEL} version. Use --version to specify."
    fi

    ok "Latest ${CHANNEL} version: ${TARGET_VERSION}"
}

# ── Phase 6: Download artifacts ────────────────────────────────────────────────

download_artifacts() {
    info "Downloading release artifacts for v${TARGET_VERSION}..."

    ARTIFACTS_DIR="$(mktemp -d)"
    TEMP_DIR="$ARTIFACTS_DIR"

    local wheel_name
    wheel_name="$(printf "$WHEEL_PATTERN" "$TARGET_VERSION")"
    local wheel_url="${RELEASES_URL}/v${TARGET_VERSION}/${wheel_name}"

    info "Downloading ${wheel_name}..."
    if ! curl -fSL --progress-bar -o "${ARTIFACTS_DIR}/${wheel_name}" "$wheel_url"; then
        die "Failed to download wheel. Verify version ${TARGET_VERSION} exists at ${REPO_URL}/releases"
    fi
    ok "Downloaded ${wheel_name}"

    info "Downloading ${CHECKSUMS_FILE}..."
    if ! curl -fSL --progress-bar -o "${ARTIFACTS_DIR}/${CHECKSUMS_FILE}" \
        "${RELEASES_URL}/v${TARGET_VERSION}/${CHECKSUMS_FILE}"; then
        warn "Checksums manifest not found — skipping verification."
    else
        ok "Downloaded ${CHECKSUMS_FILE}"
    fi

    if [ "$INSTALL_MODE" = "docker" ]; then
        local bundle_name
        bundle_name="$(printf "$DOCKER_BUNDLE_PATTERN" "$TARGET_VERSION")"
        local bundle_url="${RELEASES_URL}/v${TARGET_VERSION}/${bundle_name}"

        info "Downloading ${bundle_name}..."
        if ! curl -fSL --progress-bar -o "${ARTIFACTS_DIR}/${bundle_name}" "$bundle_url"; then
            die "Failed to download Docker bundle."
        fi
        ok "Downloaded ${bundle_name}"
    fi
}

# ── Phase 7: Verify checksums ──────────────────────────────────────────────────

verify_checksums() {
    local checksums_path="${ARTIFACTS_DIR}/${CHECKSUMS_FILE}"

    if [ ! -f "$checksums_path" ]; then
        warn "No checksums file — skipping verification."
        return
    fi

    info "Verifying checksums..."

    local failed=0
    while IFS= read -r line; do
        [ -z "$line" ] && continue
        [[ "$line" == \#* ]] && continue

        local expected_hash="${line%%  *}"
        local filename="${line#*  }"
        [ "$expected_hash" = "$line" ] && continue
        local filepath="${ARTIFACTS_DIR}/${filename}"

        if [ ! -f "$filepath" ]; then
            warn "Checksum file references ${filename} but it was not downloaded."
            failed=1
            continue
        fi

        local actual_hash
        actual_hash="$(portable_sha256 "$filepath")"
        if [ "$actual_hash" = "$expected_hash" ]; then
            ok "Checksum verified: ${filename}"
        else
            fail "Checksum mismatch: ${filename}"
            fail "  expected: ${expected_hash}"
            fail "  actual:   ${actual_hash}"
            failed=1
        fi
    done < "$checksums_path"

    if [ "$failed" -ne 0 ]; then
        die "Checksum verification failed. Artifacts may be corrupted or tampered with."
    fi

    ok "All checksums verified"
}

# ── Phase 8a: Native installation ──────────────────────────────────────────────

native_install() {
    local releases_dir="${PREFIX}/releases"
    local version_dir="${releases_dir}/${TARGET_VERSION}"
    local venv_dir="${version_dir}/venv"
    local current_link="${PREFIX}/current"
    local bin_dir

    if [ "$INSTALL_SCOPE" = "user" ]; then
        bin_dir="${PREFIX}/bin"
    else
        bin_dir="/usr/local/bin"
    fi

    local wheel_name
    wheel_name="$(printf "$WHEEL_PATTERN" "$TARGET_VERSION")"

    detect_existing_install "$current_link" "$version_dir"

    RELEASE_DIR="$version_dir"

    if [ "$DRY_RUN" = true ]; then
        info "[dry-run] Would create ${version_dir}"
        info "[dry-run] Would install wheel into ${venv_dir}"
        info "[dry-run] Would update ${current_link} -> ${version_dir}"
        info "[dry-run] Would create launcher at ${bin_dir}/devlog"
        return
    fi

    info "Installing DevLog v${TARGET_VERSION}..."

    mkdir -p "$releases_dir"
    mkdir -p "$version_dir"

    TEMP_DIR="$(mktemp -d)"
    local temp_venv="${TEMP_DIR}/venv"

    info "Creating virtual environment..."
    python3 -m venv "$temp_venv"
    ok "Virtual environment created"

    info "Installing wheel..."
    "${temp_venv}/bin/pip" install --quiet --no-cache-dir \
        "${ARTIFACTS_DIR}/${wheel_name}"
    ok "Wheel installed"

    info "Verifying devlog binary..."
    local installed_version
    installed_version="$(extract_version "${temp_venv}/bin/devlog")" || true
    if [ -z "$installed_version" ]; then
        installed_version="$("${temp_venv}/bin/python" -c "
from importlib.metadata import version
try:
    print(version('devlog'))
except Exception:
    print('')
" 2>/dev/null)" || true
    fi

    if [ -z "$installed_version" ]; then
        fail "devlog binary produced no version output"
        FAILURE_STAGE="version verification"
        rm -rf "$temp_venv"
        die "Installation verification failed."
    fi
    ok "Verified: devlog ${installed_version}"
    INSTALLED_VERSION="$installed_version"

    if [ -d "$version_dir" ] && [ "$(ls -A "$version_dir" 2>/dev/null)" ]; then
        rm -rf "$version_dir"
    fi
    mv "$temp_venv" "$venv_dir"
    ok "Release installed to ${version_dir}"

    activate_release "$version_dir" "$current_link" "$bin_dir"
}

# ── Phase 8b: Docker installation ──────────────────────────────────────────────

docker_install() {
    local install_root="${PREFIX}"
    local bundle_name
    bundle_name="$(printf "$DOCKER_BUNDLE_PATTERN" "$TARGET_VERSION")"

    if [ "$DRY_RUN" = true ]; then
        info "[dry-run] Would create Docker installation at ${install_root}"
        info "[dry-run] Would extract ${bundle_name}"
        info "[dry-run] Would create data directories"
        return
    fi

    info "Installing DevLog Docker bundle v${TARGET_VERSION}..."

    mkdir -p "$install_root"

    local bundle_path="${ARTIFACTS_DIR}/${bundle_name}"
    if [ ! -f "$bundle_path" ]; then
        die "Docker bundle not found at ${bundle_path}"
    fi

    info "Extracting bundle..."
    tar -xzf "$bundle_path" -C "$install_root"
    ok "Bundle extracted"

    local data_dirs=("data" "uploads" "themes" "backups" "logs")
    for dir in "${data_dirs[@]}"; do
        mkdir -p "${install_root}/${dir}"
    done
    ok "Data directories created"

    if [ ! -f "${install_root}/.env" ] && [ ! -f "${install_root}/devlog.env" ]; then
        if [ -f "${install_root}/.env.example" ]; then
            cp "${install_root}/.env.example" "${install_root}/.env"
            ok "Created .env from template"
        elif [ -f "${install_root}/devlog.env.example" ]; then
            cp "${install_root}/devlog.env.example" "${install_root}/devlog.env"
            ok "Created devlog.env from template"
        fi
    fi

    INSTALLED_VERSION="$TARGET_VERSION"

    echo "" >&2
    ok "DevLog Docker bundle v${TARGET_VERSION} installed to ${install_root}"
    echo "" >&2
    log "Next steps:"
    log "  cd ${install_root}"
    log "  devlog onboard --mode docker"
    log ""
    log "Or manually:"
    log "  docker compose --profile production up -d"
}

# ── Detect existing installation state ─────────────────────────────────────────

detect_existing_install() {
    local current_link="$1"
    local version_dir="$2"

    PREV_CURRENT=""
    if [ -L "$current_link" ]; then
        PREV_CURRENT="$(readlink -f "$current_link")"
    fi

    if [ -d "$version_dir" ]; then
        local existing_version
        existing_version="$(get_installed_version "$version_dir")"

        if [ -n "$existing_version" ] && [ "$existing_version" = "$TARGET_VERSION" ]; then
            if [ "$YES" = false ] && [ "$NON_INTERACTIVE" = false ]; then
                warn "Version ${TARGET_VERSION} is already installed."
                printf '\033[33mReinstall? [y/N] \033[0m' >&2
                read -r answer </dev/tty || answer="n"
                case "$answer" in
                    [yY]|[yY][eE][sS]) ;;
                    *) info "Skipping. Existing installation preserved."; exit 0 ;;
                esac
            else
                info "Version ${TARGET_VERSION} already installed. Reinstalling."
            fi
        elif [ -n "$existing_version" ]; then
            if version_gte "$existing_version" "$TARGET_VERSION"; then
                warn "Installed version ${existing_version} is newer than target ${TARGET_VERSION}."
                if [ "$YES" = false ] && [ "$NON_INTERACTIVE" = false ]; then
                    printf '\033[33mDowngrade to ${TARGET_VERSION}? [y/N] \033[0m' >&2
                    read -r answer </dev/tty || answer="n"
                    case "$answer" in
                        [yY]|[yY][eE][sS]) ;;
                        *) info "Skipping. Existing installation preserved."; exit 0 ;;
                    esac
                fi
            else
                info "Upgrading from ${existing_version} to ${TARGET_VERSION}"
            fi
        fi
    fi

    if [ -d "${version_dir}.partial" ]; then
        warn "Found partial installation from previous attempt."
        rm -rf "${version_dir}.partial"
        ok "Cleaned up partial installation"
    fi
}

get_installed_version() {
    local version_dir="$1"
    local venv_bin="${version_dir}/venv/bin/devlog"

    if [ -x "$venv_bin" ]; then
        extract_version "$venv_bin" || true
    else
        local metadata_dir="${version_dir}/venv/lib"
        if [ -d "$metadata_dir" ]; then
            find "$metadata_dir" -path "*/devlog-*/METADATA" -exec head -1 {} \; 2>/dev/null | \
                sed -n 's/^Version: *//p' | head -1 || true
        fi
    fi
}

# ── Phase 9: Atomic activation ─────────────────────────────────────────────────

activate_release() {
    local version_dir="$1"
    local current_link="$2"
    local bin_dir="$3"

    FAILURE_STAGE="activation"

    info "Activating release..."

    local parent_dir
    parent_dir="$(dirname "$current_link")"
    mkdir -p "$parent_dir"

    local tmp_link="${current_link}.tmp.$$"
    ln -sfn "$version_dir" "$tmp_link"

    if ! atomic_move "$tmp_link" "$current_link"; then
        rm -f "$tmp_link"
        ln -sfn "$version_dir" "$current_link"
    fi

    if [ ! -L "$current_link" ]; then
        if [ -n "$PREV_CURRENT" ]; then
            ln -sfn "$PREV_CURRENT" "$current_link"
            fail "Activation failed — restored previous release"
        fi
        die "Failed to create current symlink"
    fi
    ok "Current -> ${version_dir}"

    mkdir -p "$bin_dir"
    local launcher="${bin_dir}/devlog"
    local target="${current_link}/venv/bin/devlog"

    local tmp_launcher="${launcher}.tmp.$$"
    ln -sfn "$target" "$tmp_launcher"

    if ! atomic_move "$tmp_launcher" "$launcher"; then
        rm -f "$tmp_launcher"
        ln -sfn "$target" "$launcher"
    fi

    if [ ! -L "$launcher" ]; then
        fail "Failed to create launcher at ${launcher}"
        die "Launcher creation failed"
    fi
    ok "Launcher: ${launcher}"

    if [ "$INSTALL_SCOPE" = "user" ]; then
        local shell_profile=""
        if [ -f "${HOME}/.bashrc" ]; then
            shell_profile="${HOME}/.bashrc"
        elif [ -f "${HOME}/.bash_profile" ]; then
            shell_profile="${HOME}/.bash_profile"
        elif [ -f "${HOME}/.profile" ]; then
            shell_profile="${HOME}/.profile"
        fi

        if [ -n "$shell_profile" ]; then
            local bin_parent
            bin_parent="$(dirname "$bin_dir")"
            if ! grep -q "$bin_parent" "$shell_profile" 2>/dev/null; then
                warn "Add to PATH: export PATH=\"${bin_parent}:\$PATH\""
            fi
        fi
    fi

    FAILURE_STAGE=""
    ok "Release activated"
}

# ── Phase 11: Onboarding ──────────────────────────────────────────────────────

maybe_run_onboard() {
    if [ "$NO_ONBOARD" = true ]; then
        print_success
        return
    fi

    if [ "$RUN_ONBOARD" = true ]; then
        if [ -t 0 ] || [ -r /dev/tty ]; then
            info "Running onboarding..."
            if [ "$INSTALL_MODE" = "native" ]; then
                "${PREFIX}/current/venv/bin/devlog" onboard run --mode native </dev/tty || true
            else
                log "Run manually: cd ${PREFIX} && devlog onboard --mode docker"
            fi
        else
            warn "Onboarding requires a TTY. Run: devlog onboard --mode ${INSTALL_MODE}"
            print_success
        fi
    else
        print_success
    fi
}

print_success() {
    local mode_flag
    if [ "$INSTALL_MODE" = "native" ]; then
        if [ "$INSTALL_SCOPE" = "user" ]; then
            mode_flag="native --user"
        else
            mode_flag="native"
        fi
    else
        mode_flag="docker"
    fi

    echo "" >&2
    log "DevLog ${INSTALLED_VERSION} installed successfully."
    log "Next: devlog onboard --mode ${mode_flag}"
    echo "" >&2
}

# ── Main ───────────────────────────────────────────────────────────────────────

main() {
    parse_options "$@"

    detect_platform

    FAILURE_STAGE="prerequisite check"
    if [ "$INSTALL_MODE" = "native" ]; then
        select_backend
        check_native_prereqs
    else
        check_docker_prereqs
    fi

    FAILURE_STAGE="version resolution"
    resolve_version

    FAILURE_STAGE="download"
    download_artifacts

    FAILURE_STAGE="checksum verification"
    verify_checksums

    if [ "$INSTALL_MODE" = "native" ]; then
        native_install
    else
        docker_install
    fi

    TEMP_DIR=""
    FAILURE_STAGE=""

    maybe_run_onboard
}

main "$@"
