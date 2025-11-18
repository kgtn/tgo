#!/usr/bin/env bash
# Bootstrap script for one-command TGO deployment
# Usage (remote):  curl -fsSL https://your.host/bootstrap.sh | bash
# Usage (local):   bash bootstrap.sh

set -euo pipefail

# ---------- Configuration (overridable via env) ----------
REPO="${REPO:-https://github.com/tgoai/tgo-deploy.git}"
DIR="${DIR:-tgo-deploy}"
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
require_cmd() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "[FATAL] Required command not found: $1" >&2
    exit 127
  fi
}

check_prereqs() {
  require_cmd git
  require_cmd docker
  if ! docker compose version >/dev/null 2>&1; then
    echo "[FATAL] 'docker compose' plugin is required (Docker Desktop 2.20+ or Docker CLI plugin)." >&2
    echo "        Please install/upgrade Docker: https://docs.docker.com/get-docker/" >&2
    exit 1
  fi
}

# ---------- Main ----------
main() {
  check_prereqs

  # If we're already inside a tgo-deploy working dir, just run deploy.sh
  if [ -f "./deploy.sh" ] && [ -f "./docker-compose.yml" ]; then
    echo "[INFO] Detected existing tgo-deploy checkout in $(pwd). Running deploy.sh..."
    bash ./deploy.sh
    return
  fi

  # Otherwise, clone the repo to DIR and run deploy.sh
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

  echo "[RUN] bash $DIR/deploy.sh"
  bash "$DIR/deploy.sh"

  echo "\n[HINT] Use 'docker compose ps' inside $DIR to see status, and 'docker compose logs -f <service>' to tail logs."
}

main "$@"

