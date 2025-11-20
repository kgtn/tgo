#!/usr/bin/env bash
# Bootstrap script for one-command TGO deployment
# Usage (remote):  curl -fsSL https://your.host/bootstrap.sh | bash
# Usage (local):   bash bootstrap.sh

set -euo pipefail

# ---------- Configuration (overridable via env) ----------
REPO="${REPO:-https://github.com/tgoai/tgo.git}"
DIR="${DIR:-tgo}"
REF="${REF:-}"

# ---------- Notifications ----------
notify() {
  if command -v afplay >/dev/null 2>&1 && [ "$(uname)" = "Darwin" ]; then
    afplay /System/Library/Sounds/Glass.aiff || true
  else
    printf '\a' || true
  fi
}

_finish() {
  local code=$?
  if [ $code -eq 0 ]; then
    echo "\n[OK] Bootstrap completed."
  else
    echo "\n[ERROR] Bootstrap failed with code $code"
  fi
  notify
  exit $code
}
trap _finish EXIT

# ---------- Pre-flight checks ----------

OS_TYPE="unknown"
OS_DISTRO="unknown"
OS_IS_WSL=0

detect_os() {
  case "$(uname -s)" in
    Darwin)
      OS_TYPE="macos"
      ;;
    Linux)
      OS_TYPE="linux"
      if grep -qi "microsoft" /proc/version 2>/dev/null || \
         grep -qi "WSL" /proc/sys/kernel/osrelease 2>/dev/null; then
        OS_IS_WSL=1
      fi
      if [ -f /etc/os-release ]; then
        . /etc/os-release
        case "${ID:-}" in
          ubuntu|debian)
            OS_DISTRO="debian"
            ;;
          centos|rhel)
            OS_DISTRO="rhel"
            ;;
          fedora)
            OS_DISTRO="fedora"
            ;;
          arch)
            OS_DISTRO="arch"
            ;;
          *)
            OS_DISTRO="${ID:-unknown}"
            ;;
        esac
      fi
      ;;
    *)
      OS_TYPE="unknown"
      OS_DISTRO="unknown"
      ;;
  esac
}

install_git() {
  detect_os
  echo "Git is not installed. Would you like to install it now? [y/N]"
  read -r answer
  case "$answer" in
    y|Y|yes|YES) ;;
    *)
      echo "[FATAL] Git is required. Please install Git and re-run this script." >&2
      exit 1
      ;;
  esac

  if [ "$OS_TYPE" = "macos" ]; then
    if command -v brew >/dev/null 2>&1; then
      echo "[INFO] Installing Git via Homebrew..."
      set +e
      brew install git
      status=$?
      set -e
      if [ $status -ne 0 ]; then
        echo "[FATAL] Failed to install Git via Homebrew. Please install it manually." >&2
        echo "        https://git-scm.com/downloads" >&2
        exit 1
      fi
    else
      echo "[INFO] On macOS you can install Git by running: xcode-select --install" >&2
      echo "      Or install Homebrew and then run: brew install git" >&2
      echo "      See: https://git-scm.com/download/mac" >&2
      exit 1
    fi
  elif [ "$OS_TYPE" = "linux" ]; then
    if ! command -v sudo >/dev/null 2>&1; then
      echo "[FATAL] sudo is not available. Please ask your system administrator to install Git." >&2
      exit 1
    fi
    echo "[INFO] Installing Git using the system package manager..."
    set +e
    case "$OS_DISTRO" in
      debian)
        sudo apt-get update && sudo apt-get install -y git
        ;;
      rhel|fedora)
        if command -v dnf >/dev/null 2>&1; then
          sudo dnf install -y git
        else
          sudo yum install -y git
        fi
        ;;
      arch)
        sudo pacman -Sy --noconfirm git
        ;;
      *)
        echo "[WARN] Unsupported or unknown Linux distribution ($OS_DISTRO)." >&2
        echo "       Please install Git manually: https://git-scm.com/download/linux" >&2
        set -e
        exit 1
        ;;
    esac
    status=$?
    set -e
    if [ $status -ne 0 ]; then
      echo "[FATAL] Automatic Git installation failed. Please install Git manually." >&2
      echo "        https://git-scm.com/downloads" >&2
      exit 1
    fi
  else
    echo "[FATAL] Unsupported OS. Please install Git manually: https://git-scm.com/downloads" >&2
    exit 1
  fi

  if ! command -v git >/dev/null 2>&1; then
    echo "[FATAL] Git installation did not succeed. Please install it manually." >&2
    exit 1
  fi

  echo "[INFO] Git installation looks OK: $(git --version 2>/dev/null || echo 'version check failed')"
}

install_docker() {
  detect_os
  echo "Docker is not installed. Would you like to install it now? [y/N]"
  read -r answer
  case "$answer" in
    y|Y|yes|YES) ;;
    *)
      echo "[FATAL] Docker is required. Please install Docker and re-run this script." >&2
      echo "        https://docs.docker.com/get-docker/" >&2
      exit 1
      ;;
  esac

  if [ "$OS_TYPE" = "macos" ]; then
    echo "[INFO] Please install Docker Desktop for macOS from:" >&2
    echo "       https://docs.docker.com/desktop/install/mac-install/" >&2
    exit 1
  elif [ "$OS_TYPE" = "linux" ]; then
    if [ "$OS_IS_WSL" -eq 1 ]; then
      echo "[WARN] Detected WSL2 environment. The recommended setup is Docker Desktop for Windows with WSL2 integration:" >&2
      echo "       https://docs.docker.com/desktop/wsl/" >&2
    fi

    if ! command -v sudo >/dev/null 2>&1; then
      echo "[FATAL] sudo is not available. Please ask your system administrator to install Docker." >&2
      exit 1
    fi

    echo "[INFO] Installing Docker using the system package manager..."
    set +e
    case "$OS_DISTRO" in
      debian)
        sudo apt-get update && sudo apt-get install -y docker.io docker-compose-plugin
        ;;
      rhel|fedora)
        if command -v dnf >/dev/null 2>&1; then
          sudo dnf install -y docker docker-compose-plugin
        else
          sudo yum install -y docker docker-compose-plugin
        fi
        ;;
      arch)
        sudo pacman -Sy --noconfirm docker docker-compose
        ;;
      *)
        echo "[WARN] Unsupported or unknown Linux distribution ($OS_DISTRO)." >&2
        echo "       Please install Docker manually: https://docs.docker.com/engine/install/" >&2
        set -e
        exit 1
        ;;
    esac
    status=$?
    set -e
    if [ $status -ne 0 ]; then
      echo "[FATAL] Automatic Docker installation failed. Please install Docker manually:" >&2
      echo "        https://docs.docker.com/engine/install/" >&2
      exit 1
    fi

    if command -v systemctl >/dev/null 2>&1; then
      echo "[INFO] Starting and enabling Docker service (systemd)..."
      sudo systemctl start docker || true
      sudo systemctl enable docker || true
    fi

    if command -v getent >/dev/null 2>&1 && getent group docker >/dev/null 2>&1; then
      echo "[INFO] Adding current user to 'docker' group (you may need to log out and back in)."
      sudo usermod -aG docker "$USER" || true
    fi
  else
    echo "[FATAL] Unsupported OS. Please install Docker manually: https://docs.docker.com/get-docker/" >&2
    exit 1
  fi

  if ! command -v docker >/dev/null 2>&1; then
    echo "[FATAL] Docker installation did not succeed. Please install it manually." >&2
    exit 1
  fi

  echo "[INFO] Docker installation looks OK: $(docker --version 2>/dev/null || echo 'version check failed')"
}

install_docker_compose() {
  detect_os
  echo "Docker Compose plugin is not installed. Would you like to install it now? [y/N]"
  read -r answer
  case "$answer" in
    y|Y|yes|YES) ;;
    *)
      echo "[FATAL] Docker Compose plugin is required. Please install it and re-run this script." >&2
      echo "        https://docs.docker.com/compose/install/" >&2
      exit 1
      ;;
  esac

  if [ "$OS_TYPE" = "macos" ]; then
    echo "[INFO] On macOS the Docker Compose plugin is bundled with Docker Desktop." >&2
    echo "       Please install or upgrade Docker Desktop:" >&2
    echo "       https://docs.docker.com/desktop/install/mac-install/" >&2
    exit 1
  elif [ "$OS_TYPE" = "linux" ]; then
    if ! command -v sudo >/dev/null 2>&1; then
      echo "[FATAL] sudo is not available. Please ask your system administrator to install Docker Compose plugin." >&2
      exit 1
    fi

    echo "[INFO] Installing Docker Compose plugin using the system package manager..."
    set +e
    case "$OS_DISTRO" in
      debian)
        sudo apt-get update && sudo apt-get install -y docker-compose-plugin
        ;;
      rhel|fedora)
        if command -v dnf >/dev/null 2>&1; then
          sudo dnf install -y docker-compose-plugin
        else
          sudo yum install -y docker-compose-plugin
        fi
        ;;
      arch)
        sudo pacman -Sy --noconfirm docker-compose
        ;;
      *)
        echo "[WARN] Unsupported or unknown Linux distribution ($OS_DISTRO)." >&2
        echo "       Please install Docker Compose manually: https://docs.docker.com/compose/install/" >&2
        set -e
        exit 1
        ;;
    esac
    status=$?
    set -e
    if [ $status -ne 0 ]; then
      echo "[FATAL] Automatic Docker Compose plugin installation failed. Please install it manually:" >&2
      echo "        https://docs.docker.com/compose/install/" >&2
      exit 1
    fi
  else
    echo "[FATAL] Unsupported OS. Please install Docker Compose plugin manually: https://docs.docker.com/compose/install/" >&2
    exit 1
  fi

  if ! docker compose version >/dev/null 2>&1; then
    echo "[FATAL] Docker Compose plugin installation did not succeed. Please install it manually." >&2
    exit 1
  fi

  echo "[INFO] Docker Compose plugin installation looks OK."
}

check_prereqs() {
  if ! command -v git >/dev/null 2>&1; then
    install_git
  fi

  if ! command -v docker >/dev/null 2>&1; then
    install_docker
  fi

  if ! docker compose version >/dev/null 2>&1; then
    install_docker_compose
  fi
}

# ---------- Main ----------
main() {
  check_prereqs

  # If we're already inside a tgo-deploy working dir, run tgo.sh install
  if [ -f "./tgo.sh" ] && [ -f "./docker-compose.yml" ]; then
    echo "[INFO] Detected existing tgo-deploy checkout in $(pwd). Running ./tgo.sh install..."
    ./tgo.sh install
    return
  fi


  # Otherwise, clone the repo to DIR and run tgo.sh install
  if [ -d "$DIR/.git" ]; then
    echo "[OK] Repository already present: $DIR"
  else
    echo "[CLONE] $REPO -> $DIR"
    git clone --depth=1 "$REPO" "$DIR"
  fi

  if [ -n "$REF" ]; then
    echo "[CHECKOUT] $REF"
    git -C "$DIR" fetch --depth=1 origin "$REF" || true
    git -C "$DIR" checkout -q "$REF"
  fi

  if [ -f "$DIR/tgo.sh" ]; then
    echo "[RUN] (cd $DIR && ./tgo.sh install)"
    (cd "$DIR" && ./tgo.sh install)
  elif [ -f "$DIR/deploy.sh" ]; then
    echo "[RUN] bash $DIR/deploy.sh (legacy)"
    bash "$DIR/deploy.sh"
  else
    echo "[FATAL] Neither tgo.sh nor deploy.sh found in $DIR" >&2
    exit 1
  fi

  echo "\n[HINT] Use 'docker compose ps' inside $DIR to see status, and 'docker compose logs -f <service>' to tail logs."
}

main "$@"

