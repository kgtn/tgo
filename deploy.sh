#!/usr/bin/env bash
set -euo pipefail

# Move to script dir
cd "$(dirname "$0")"

# Prepare .env
if [ ! -f .env ]; then
  cp .env.example .env
  echo "Created .env from .env.example. Edit it if needed."
fi



# Ensure API SECRET_KEY is generated on first deploy
ensure_api_secret_key() {
  local file="envs/tgo-api.env"
  [ -f "$file" ] || { echo "[WARN] $file not found; skipping SECRET_KEY generation"; return 0; }
  local placeholder="ad6b1be1e4f9d2b03419e0876d0d2a19c647c7ef1dd1d2d9d3f98a09b7b1c0e7"
  local current
  current=$(grep -E '^SECRET_KEY=' "$file" | head -n1 | cut -d= -f2- || true)
  if [ -z "$current" ] || [ "$current" = "$placeholder" ] || [ "$current" = "changeme" ] || [ ${#current} -lt 32 ]; then
    local newkey
    if command -v openssl >/dev/null 2>&1; then
      newkey=$(openssl rand -hex 32)
    elif command -v python3 >/dev/null 2>&1; then
      newkey=$(python3 - <<'PY'
import secrets; print(secrets.token_hex(32))
PY
)
    elif command -v python >/dev/null 2>&1; then
      newkey=$(python - <<'PY'
import secrets; print(secrets.token_hex(32))
PY
)
    else
      newkey=$(dd if=/dev/urandom bs=32 count=1 2>/dev/null | xxd -p -c 64 2>/dev/null || date +%s | shasum -a 256 | awk '{print $1}' | cut -c1-64)
    fi
    local tmp="${file}.tmp"
    if grep -qE '^SECRET_KEY=' "$file"; then
      awk -v nk="$newkey" 'BEGIN{FS=OFS="="} /^SECRET_KEY=/{print "SECRET_KEY",nk; next} {print $0}' "$file" > "$tmp" && mv "$tmp" "$file"
    else
      printf "\nSECRET_KEY=%s\n" "$newkey" >> "$file"
    fi
    echo "[OK] Generated new SECRET_KEY for tgo-api"
  else
    echo "[OK] SECRET_KEY already set and non-placeholder; keep existing"
  fi
}

# Ensure envs directory exists (copy from envs.docker on first run)
if [ ! -d "envs" ]; then
  if [ -d "envs.docker" ]; then
    cp -R "envs.docker" "envs"
    echo "[OK] Created envs/ from envs.docker"
  else
    echo "[WARN] envs/ not found and envs.docker/ missing; proceeding without copying"
  fi
fi


# Generate a secure SECRET_KEY for tgo-api if needed
ensure_api_secret_key


# Build & start all services
docker compose --env-file .env up -d --build

echo "\nAll services are starting. Use 'docker compose ps' and logs to check status."

