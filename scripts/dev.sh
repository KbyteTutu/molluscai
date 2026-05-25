#!/usr/bin/env bash
# MolluscAI dev toolbox - one script for the whole debug/rebuild/run loop.
set -euo pipefail

SCRIPT_PATH="$(readlink -f "${BASH_SOURCE[0]}")"
ROOT="$(cd "$(dirname "$SCRIPT_PATH")/.." && pwd)"
cd "$ROOT"

BASE_IMAGE="molluscai-base:v0.3"
BASE_DOCKERFILE="infra/docker/base.Dockerfile"
COMPOSE="docker compose"
COMPOSE_PROD="$COMPOSE -f docker-compose.yml -f docker-compose.prod.yml"

NETWORK_NAME="molluscai-net"
VOLUMES=(molluscai-postgres-data molluscai-redis-data molluscai-minio-data)

PG_CONTAINER="molluscai-postgres"
REDIS_CONTAINER="molluscai-redis"
BACKEND_CONTAINER="molluscai-backend"
WORKER_CONTAINER="molluscai-celery-worker"
BEAT_CONTAINER="molluscai-celery-beat"
MINIO_CONTAINER="molluscai-minio"

PG_USER="${POSTGRES_USER:-mollusc}"
PG_DB="${POSTGRES_DB:-molluscai}"
API_BASE="http://localhost:${BACKEND_PORT:-8000}/api/v1"

env_get() {
  local key="$1"
  [[ -f "$ROOT/.env" ]] || { printf '%s' ""; return 0; }
  # grep returns 1 when no match; under `set -euo pipefail` that would kill
  # callers using $(env_get …). Treat "missing key" as empty string.
  { grep -E "^${key}=" "$ROOT/.env" || true; } | head -1 | cut -d= -f2-
}

# ─── tty colors ─────────────────────────────────────────────
if [[ -t 1 ]]; then
  C_DIM=$'\e[2m'; C_OK=$'\e[32m'; C_ERR=$'\e[31m'; C_WARN=$'\e[33m'; C_HEAD=$'\e[1;36m'; C_END=$'\e[0m'
else
  C_DIM=''; C_OK=''; C_ERR=''; C_WARN=''; C_HEAD=''; C_END=''
fi
log()  { printf '%s==>%s %s\n' "$C_HEAD" "$C_END" "$*"; }
ok()   { printf '%s✓%s %s\n' "$C_OK" "$C_END" "$*"; }
warn() { printf '%s!%s %s\n' "$C_WARN" "$C_END" "$*"; }
err()  { printf '%s✗%s %s\n' "$C_ERR" "$C_END" "$*" >&2; }
die()  { err "$*"; exit 1; }

# ─── helpers ────────────────────────────────────────────────
base_image_exists() { docker image inspect "$BASE_IMAGE" >/dev/null 2>&1; }

base_image_stale() {
  base_image_exists || return 0
  local img_ts req_ts
  img_ts=$(docker image inspect -f '{{.Created}}' "$BASE_IMAGE" | xargs -I{} date -d {} +%s 2>/dev/null || echo 0)
  req_ts=$(stat -c %Y backend/requirements.txt 2>/dev/null || stat -f %m backend/requirements.txt)
  [[ "$req_ts" -gt "$img_ts" ]]
}

ensure_base() {
  if base_image_exists && ! base_image_stale; then
    ok "base image $BASE_IMAGE up-to-date"
    return
  fi
  if ! base_image_exists; then
    log "base image missing - building..."
  else
    warn "requirements.txt newer than base image - rebuilding..."
  fi
  docker build -f "$BASE_DOCKERFILE" -t "$BASE_IMAGE" .
  ok "base image built"
}

ensure_network() {
  if docker network inspect "$NETWORK_NAME" >/dev/null 2>&1; then
    ok "network $NETWORK_NAME exists"
  else
    log "creating network $NETWORK_NAME..."
    docker network create "$NETWORK_NAME" >/dev/null
    ok "network created"
  fi
}

ensure_volumes() {
  local minio_path
  minio_path="$(env_get MINIO_DATA_PATH)"
  if [[ -n "$minio_path" ]]; then
    if [[ ! -d "$minio_path" ]]; then
      err "MINIO_DATA_PATH=$minio_path is set but the directory does not exist."
      err "Create it on the host first (e.g. mkdir -p $minio_path) or unset MINIO_DATA_PATH to fall back to a docker named volume."
      die "aborted"
    fi
    if ! touch "$minio_path/.molluscai-write-test" 2>/dev/null; then
      err "MINIO_DATA_PATH=$minio_path is not writable by the current user."
      err "Fix permissions (e.g. chmod 1777 $minio_path on a shared NAS, or chown to the minio container UID)."
      die "aborted"
    fi
    rm -f "$minio_path/.molluscai-write-test"
    ok "minio bind mount: $minio_path (writable)"
  fi
  for v in "${VOLUMES[@]}"; do
    if [[ -n "$minio_path" && "$v" == "molluscai-minio-data" ]]; then
      ok "skipping volume $v (MINIO_DATA_PATH set)"
      continue
    fi
    if docker volume inspect "$v" >/dev/null 2>&1; then
      ok "volume $v exists"
    else
      log "creating volume $v..."
      docker volume create "$v" >/dev/null
      ok "volume $v created"
    fi
  done
}

ensure_env() {
  if [[ ! -f "$ROOT/.env" ]]; then
    err ".env missing. Generate one with:"
    err "    ./dev prod-secrets > .env  # then fill in API keys"
    die "aborted"
  fi

  local required_nonempty=(POSTGRES_PASSWORD MINIO_ROOT_PASSWORD JWT_SECRET_KEY JWT_REFRESH_SECRET_KEY ENCRYPTION_KEY)
  local required_no_placeholder=(JWT_SECRET_KEY JWT_REFRESH_SECRET_KEY ENCRYPTION_KEY)
  local errors=0

  for key in "${required_nonempty[@]}"; do
    local val
    val=$(grep -E "^${key}=" "$ROOT/.env" | head -1 | cut -d= -f2-)
    if [[ -z "$val" ]]; then
      err ".env: ${key} is missing or empty (production deploys MUST set this)"
      errors=$((errors + 1))
    fi
  done

  for key in "${required_no_placeholder[@]}"; do
    if grep -qE "^${key}=replace-me" "$ROOT/.env"; then
      err ".env: ${key} still has 'replace-me-...' placeholder."
      err "Generate new ones with: ./dev prod-secrets"
      errors=$((errors + 1))
    fi
  done

  [[ $errors -eq 0 ]] || die "aborted ($errors .env validation error(s))"
  ok ".env validated"
}

ensure_infra() {
  ensure_env
  ensure_network
  ensure_volumes
}

container_running() { docker ps --format '{{.Names}}' | grep -qx "$1"; }

require_running() {
  container_running "$1" || die "$1 is not running. Try: $0 up"
}

get_admin_token() {
  local user="${ADMIN_USERNAME:-}" pass="${ADMIN_PASSWORD:-}"
  [[ -n "$user" && -n "$pass" ]] || die "Set ADMIN_USERNAME and ADMIN_PASSWORD env vars to use this command"
  curl -sf -X POST "$API_BASE/auth/login" \
    -H "Content-Type: application/json" \
    -d "{\"username\":\"$user\",\"password\":\"$pass\"}" \
    | python3 -c "import sys,json;print(json.load(sys.stdin)['access_token'])"
}

# ─── subcommands ────────────────────────────────────────────

cmd_up() {
  ensure_infra
  ensure_base
  log "starting full stack..."
  $COMPOSE up -d --build
  ok "stack started"
  cmd_status
}

cmd_down() {
  log "stopping stack..."
  $COMPOSE down
  ok "stopped"
}

cmd_nuke() {
  warn "this will DELETE all data: postgres / redis / minio volumes, the molluscai-net network, AND all molluscai-* images"
  printf 'Type %snuke%s to confirm: ' "$C_ERR" "$C_END"
  local confirm; read -r confirm
  [[ "$confirm" == "nuke" ]] || die "aborted"
  $COMPOSE down --remove-orphans 2>/dev/null || true
  rm -f "$ROOT/backend/celerybeat-schedule"*
  for v in "${VOLUMES[@]}"; do docker volume rm -f "$v" 2>/dev/null || true; done
  docker network rm "$NETWORK_NAME" 2>/dev/null || true
  docker image rm -f "$BASE_IMAGE" 2>/dev/null || true
  docker image rm -f molluscai-backend:latest molluscai-celery-worker:latest molluscai-celery-beat:latest molluscai-frontend:latest 2>/dev/null || true
  ok "nuked. run '$0 up' to start fresh"
}

cmd_rebuild() {
  log "force rebuilding base + app images..."
  docker build --no-cache -f "$BASE_DOCKERFILE" -t "$BASE_IMAGE" .
  $COMPOSE build --no-cache backend celery-worker celery-beat
  $COMPOSE up -d backend celery-worker celery-beat
  ok "rebuilt and restarted"
}

cmd_restart() {
  local svc="${1:-}"
  if [[ -z "$svc" ]]; then
    log "recreating backend + celery-worker + celery-beat..."
    $COMPOSE up -d --force-recreate backend celery-worker celery-beat
  else
    log "recreating $svc..."
    $COMPOSE up -d --force-recreate "$svc"
  fi
  ok "restarted"
}

cmd_logs() {
  local svc="${1:-backend}"
  log "tailing logs for $svc (Ctrl+C to stop)..."
  $COMPOSE logs -f --tail=100 "$svc"
}

cmd_status() {
  log "compose services:"
  $COMPOSE ps
  echo
  log "health checks:"
  if container_running "$PG_CONTAINER"; then
    if docker exec "$PG_CONTAINER" pg_isready -U "$PG_USER" -d "$PG_DB" >/dev/null 2>&1; then
      local count
      count=$(docker exec "$PG_CONTAINER" psql -U "$PG_USER" -d "$PG_DB" -tAc "SELECT COUNT(*) FROM auctions" 2>/dev/null || echo "?")
      ok "postgres: ready, auctions=$count"
    else
      err "postgres: NOT ready"
    fi
  else
    err "postgres: container not running"
  fi
  if container_running "$REDIS_CONTAINER"; then
    if docker exec "$REDIS_CONTAINER" redis-cli ping 2>/dev/null | grep -q PONG; then
      ok "redis: PONG"
    else
      err "redis: no PONG"
    fi
  else
    err "redis: container not running"
  fi
  if container_running "$MINIO_CONTAINER"; then
    if docker exec "$MINIO_CONTAINER" curl -sf http://localhost:9000/minio/health/live >/dev/null 2>&1; then
      ok "minio: live"
    else
      err "minio: unhealthy"
    fi
  else
    err "minio: container not running"
  fi
  if container_running "$BACKEND_CONTAINER"; then
    if curl -sf "http://localhost:${BACKEND_PORT:-8000}/health" >/dev/null 2>&1; then
      ok "backend: /health OK"
    else
      err "backend: /health failed"
    fi
  else
    err "backend: container not running"
  fi
  if container_running "$WORKER_CONTAINER"; then
    ok "celery-worker: running"
  else
    err "celery-worker: not running"
  fi
}

cmd_psql() {
  require_running "$PG_CONTAINER"
  local flags="-i"
  [[ -t 0 && -t 1 ]] && flags="-it"
  docker exec $flags "$PG_CONTAINER" psql -U "$PG_USER" -d "$PG_DB" "$@"
}

cmd_redis() {
  require_running "$REDIS_CONTAINER"
  local flags="-i"
  [[ -t 0 && -t 1 ]] && flags="-it"
  docker exec $flags "$REDIS_CONTAINER" redis-cli "$@"
}

cmd_shell() {
  local svc="${1:-backend}"
  local container="molluscai-$svc"
  require_running "$container"
  docker exec -it "$container" bash
}

cmd_seed() {
  require_running "$PG_CONTAINER"
  local backup="legacy/postgres_backup.sql"
  [[ -f "$backup" ]] || die "missing $backup"

  local existing
  existing=$(docker exec "$PG_CONTAINER" psql -U "$PG_USER" -d "$PG_DB" -tAc "SELECT COUNT(*) FROM auctions")
  if [[ "$existing" -gt 100 ]]; then
    warn "auctions table already has $existing rows. Continue? [y/N]"
    local c; read -r c
    [[ "$c" == "y" || "$c" == "Y" ]] || die "aborted"
  fi

  log "copying $backup into postgres container..."
  docker cp "$backup" "$PG_CONTAINER:/tmp/backup.sql"

  log "creating staging table + extracting COPY block..."
  docker exec "$PG_CONTAINER" psql -U "$PG_USER" -d "$PG_DB" -c "
    DROP TABLE IF EXISTS shellauction_staging;
    CREATE TABLE shellauction_staging (
      id integer, item integer, image text, name text, family text,
      size text, locality text, note text, seller text,
      start_price integer, current_price integer, end_date text,
      owner text, deal_date date
    );" >/dev/null

  docker exec "$PG_CONTAINER" bash -c "awk '
    /^COPY public\.shellauction/ {
      print \"COPY shellauction_staging (id, item, image, name, family, size, locality, note, seller, start_price, current_price, end_date, owner, deal_date) FROM stdin;\"; in_copy=1; next
    }
    in_copy && /^\\\\\.\$/ { print; in_copy=0; exit }
    in_copy { print }
  ' /tmp/backup.sql > /tmp/staging_copy.sql"

  log "loading staging data (this takes ~30s)..."
  docker exec "$PG_CONTAINER" psql -U "$PG_USER" -d "$PG_DB" -f /tmp/staging_copy.sql >/dev/null

  log "transforming staging -> auctions..."
  docker exec "$PG_CONTAINER" psql -U "$PG_USER" -d "$PG_DB" -c "
    INSERT INTO auctions (item_no, name, family, size, locality, note, seller,
                          start_price, final_price, end_date, buyer, images_origin)
    SELECT DISTINCT ON (item)
      item,
      NULLIF(name, ''),  NULLIF(family, ''), NULLIF(size, ''), NULLIF(locality, ''),
      NULLIF(note, ''),  NULLIF(seller, ''),
      start_price::numeric,
      current_price::numeric,
      CASE WHEN end_date ~ '^[0-9]{2}-[0-9]{2}-[0-9]{4}\$' THEN TO_DATE(end_date, 'DD-MM-YYYY') ELSE NULL END,
      NULLIF(owner, ''),
      CASE WHEN NULLIF(image, '') IS NOT NULL THEN ARRAY[image] ELSE NULL END
    FROM shellauction_staging
    WHERE item IS NOT NULL
    ORDER BY item, id DESC
    ON CONFLICT (item_no) DO NOTHING;" >/dev/null

  docker exec "$PG_CONTAINER" psql -U "$PG_USER" -d "$PG_DB" -c "DROP TABLE shellauction_staging;" >/dev/null
  docker exec "$PG_CONTAINER" rm -f /tmp/backup.sql /tmp/staging_copy.sql

  local count
  count=$(docker exec "$PG_CONTAINER" psql -U "$PG_USER" -d "$PG_DB" -tAc "SELECT COUNT(*) FROM auctions")
  ok "seed complete. auctions=$count"
}

cmd_scrape() {
  local n="${1:-50}"
  local token; token=$(get_admin_token)
  log "triggering scraper (batch_size=$n)..."
  curl -sf -X POST "$API_BASE/admin/scraper/run" \
    -H "Authorization: Bearer $token" \
    -H "Content-Type: application/json" \
    -d "{\"batch_size\":$n}" | python3 -m json.tool
}

cmd_images() {
  local n="${1:-20}"
  local token; token=$(get_admin_token)
  log "triggering image downloader (batch_size=$n)..."
  curl -sf -X POST "$API_BASE/admin/scraper/download-images" \
    -H "Authorization: Bearer $token" \
    -H "Content-Type: application/json" \
    -d "{\"batch_size\":$n}" | python3 -m json.tool
}

cmd_test() {
  log "end-to-end smoke test..."
  local ts="t$(date +%s)"
  local user="dev_$ts" pass="DevPassword123!" email="dev_$ts@example.com"

  log "register $user..."
  local body http
  body=$(curl -sS -X POST "$API_BASE/auth/register" \
    -H "Content-Type: application/json" \
    -d "{\"username\":\"$user\",\"email\":\"$email\",\"password\":\"$pass\"}" \
    -w "\n%{http_code}")
  http=$(echo "$body" | tail -1)
  body=$(echo "$body" | head -n -1)
  [[ "$http" == "201" ]] || { err "register HTTP=$http: $body"; return 1; }
  ok "register 201"

  local token
  token=$(echo "$body" | python3 -c "import sys,json;print(json.load(sys.stdin)['access_token'])")

  http=$(curl -s "$API_BASE/auth/me" -H "Authorization: Bearer $token" -o /dev/null -w "%{http_code}")
  [[ "$http" == "200" ]] || { err "/auth/me HTTP=$http"; return 1; }
  ok "/auth/me 200"

  http=$(curl -s -X POST "$API_BASE/auction/search" \
    -H "Authorization: Bearer $token" -H "Content-Type: application/json" \
    -d '{"limit":1}' -o /dev/null -w "%{http_code}")
  [[ "$http" == "200" ]] || { err "/auction/search HTTP=$http"; return 1; }
  ok "/auction/search 200"

  ok "all smoke tests passed"
}

# ─── production ──────────────────────────────────────────────

cmd_prod_up() {
  ensure_infra
  ensure_base
  rm -f "$ROOT/backend/celerybeat-schedule"*
  log "starting production stack..."
  $COMPOSE_PROD up -d --build
  ok "production stack started"
  cmd_prod_status
  echo
  ok "next step: import data with"
  ok "    ./dev prod-import data_import/worms_mollusca.sqlite[.gz] data_import/postgres_backup.sql[.gz]"
}

cmd_prod_nuke() {
  local minio_path
  minio_path="$(env_get MINIO_DATA_PATH)"
  warn "PRODUCTION nuke: stops stack, deletes ALL volumes, network, and molluscai-* images."
  warn "Postgres / Redis / MinIO data will be permanently destroyed."
  if [[ -n "$minio_path" ]]; then
    warn "MINIO_DATA_PATH=$minio_path is set: that host path is NOT touched."
    warn "If you also want to wipe MinIO data on the NAS, run manually:  rm -rf $minio_path/*"
  fi
  printf 'Type %sprod-nuke%s to confirm: ' "$C_ERR" "$C_END"
  local confirm; read -r confirm
  [[ "$confirm" == "prod-nuke" ]] || die "aborted"
  $COMPOSE_PROD down --remove-orphans 2>/dev/null || true
  rm -f "$ROOT/backend/celerybeat-schedule"*
  for v in "${VOLUMES[@]}"; do docker volume rm -f "$v" 2>/dev/null || true; done
  docker network rm "$NETWORK_NAME" 2>/dev/null || true
  docker image rm -f "$BASE_IMAGE" 2>/dev/null || true
  docker image rm -f molluscai-backend:latest molluscai-celery-worker:latest molluscai-celery-beat:latest molluscai-frontend:latest 2>/dev/null || true
  ok "production stack nuked. run '$0 prod-up' to redeploy from scratch"
  [[ -n "$minio_path" ]] && ok "(MinIO bind-mount data at $minio_path was preserved.)"
}

cmd_prod_build() {
  log "building production images..."
  docker build -f "$BASE_DOCKERFILE" -t "$BASE_IMAGE" .
  $COMPOSE_PROD build --no-cache backend frontend
  ok "production images built"
}

cmd_prod_down() {
  log "stopping production stack..."
  $COMPOSE_PROD down
  ok "stopped"
}

cmd_prod_restart() {
  local svc="${1:-}"
  if [[ -z "$svc" ]]; then
    log "recreating backend + celery-worker + celery-beat (picks up compose/.env changes)..."
    $COMPOSE_PROD up -d --force-recreate backend celery-worker celery-beat
  else
    log "recreating $svc (picks up compose/.env changes)..."
    $COMPOSE_PROD up -d --force-recreate "$svc"
  fi
  ok "restarted"
}

cmd_prod_logs() {
  local svc="${1:-backend}"
  log "tailing prod logs for $svc (Ctrl+C to stop)..."
  $COMPOSE_PROD logs -f --tail=100 "$svc"
}

cmd_prod_status() {
  $COMPOSE_PROD ps
}

cmd_prod_secrets() {
  bash "$ROOT/scripts/generate-secrets.sh"
}

cmd_backup() {
  require_running "$PG_CONTAINER"
  local out="${1:-backups/$(date +%Y%m%d_%H%M%S).sql.gz}"
  mkdir -p "$(dirname "$out")"
  log "dumping postgres -> $out..."
  docker exec "$PG_CONTAINER" pg_dump -U "$PG_USER" -d "$PG_DB" | gzip > "$out"
  ok "backup written: $out ($(du -h "$out" | cut -f1))"
}

cmd_restore() {
  local file="${1:-}"
  [[ -n "$file" && -f "$file" ]] || die "usage: $0 restore <backup.sql.gz>"
  require_running "$PG_CONTAINER"
  warn "this will DROP all current data in $PG_DB. Continue? [y/N]"
  local c; read -r c
  [[ "$c" == "y" || "$c" == "Y" ]] || die "aborted"
  log "restoring from $file..."
  docker exec "$PG_CONTAINER" psql -U "$PG_USER" -d postgres -c "DROP DATABASE IF EXISTS $PG_DB WITH (FORCE); CREATE DATABASE $PG_DB;" >/dev/null
  gunzip -c "$file" | docker exec -i "$PG_CONTAINER" psql -U "$PG_USER" -d "$PG_DB" >/dev/null
  ok "restored"
}

cmd_worms_import() {
  local input="${1:-}"
  [[ -z "$input" ]] && die "usage: $0 worms-import <path/to/worms_mollusca.sqlite[.gz]>"
  bash "$ROOT/scripts/prod_import.sh" "$input" ""
}

cmd_prod_import() {
  bash "$ROOT/scripts/prod_import.sh" "$@"
}

cmd_clean_vectors() {
  require_running "$PG_CONTAINER"
  local target="${1:-}"
  if [[ -z "$target" ]]; then
    err "usage: $0 clean-vectors {auctions|taxa|all}"
    err "  auctions  — truncate auction_embeddings (~21 GB freed)"
    err "  taxa      — truncate taxa_embeddings (~4 GB freed)"
    err "  all       — truncate ALL vector tables (auction + taxa + text + image chunks)"
    die "missing target"
  fi
  case "$target" in
    auctions) ;;
    taxa) ;;
    all) ;;
    *) die "invalid target '$target'. Must be: auctions | taxa | all" ;;
  esac

  warn "This will PERMANENTLY DELETE vector data: $target"
  warn "Embedding API costs already spent will NOT be refunded."
  printf 'Type %sclean-vectors%s to confirm: ' "$C_ERR" "$C_END"
  local confirm; read -r confirm
  [[ "$confirm" == "clean-vectors" ]] || die "aborted"

  local before after freed
  before=$(docker exec "$PG_CONTAINER" psql -U "$PG_USER" -d "$PG_DB" -tAc \
    "SELECT pg_size_pretty(pg_database_size('$PG_DB'))")

  case "$target" in
    auctions)
      docker exec "$PG_CONTAINER" psql -U "$PG_USER" -d "$PG_DB" -c "TRUNCATE auction_embeddings;" >/dev/null
      ;;
    taxa)
      docker exec "$PG_CONTAINER" psql -U "$PG_USER" -d "$PG_DB" -c "TRUNCATE taxa_embeddings;" >/dev/null
      ;;
    all)
      docker exec "$PG_CONTAINER" psql -U "$PG_USER" -d "$PG_DB" \
        -c "TRUNCATE auction_embeddings, taxa_embeddings, text_chunks, image_chunks;" >/dev/null
      ;;
  esac

  after=$(docker exec "$PG_CONTAINER" psql -U "$PG_USER" -d "$PG_DB" -tAc \
    "SELECT pg_size_pretty(pg_database_size('$PG_DB'))")
  ok "vectors cleaned. DB size: $before → $after"
  warn "Run 'VACUUM FULL' later to reclaim disk space if needed."
}

cmd_help() {
  cat <<EOF
${C_HEAD}MolluscAI dev toolbox${C_END}

${C_HEAD}Lifecycle:${C_END}
  up                start full stack (builds base image if missing/stale)
  down              stop stack
  nuke              wipe ALL data and images (requires typing 'nuke')
  rebuild           force --no-cache rebuild of base + app images
  restart [svc]     restart service (default: backend + celery-worker)

${C_HEAD}Observability:${C_END}
  logs [svc]        tail logs (default: backend)
  status            health check across all services

${C_HEAD}Production (VPS deployment):${C_END}
  prod-up            start prod stack (auto-creates network + volumes; checks .env)
  prod-build         build base image + --no-cache backend/frontend
  prod-down          stop production stack (network + volumes preserved)
  prod-nuke          DESTRUCTIVE: stop + delete volumes + network + images (requires 'prod-nuke')
  prod-restart [svc] restart service (default: backend + frontend)
  prod-logs [svc]    tail production logs (default: backend)
  prod-status        show production compose ps
  prod-secrets       generate secure random secrets for .env

${C_HEAD}Shells:${C_END}
  psql [args...]    open psql in postgres container
  redis [args...]   open redis-cli
  shell [svc]       bash into container (default: backend)

${C_HEAD}Data:${C_END}
  seed              import legacy/postgres_backup.sql into auctions
  worms-import <f>  import a WoRMS sqlite (.sqlite or .sqlite.gz) into taxa.*
  prod-import [w] [b]  full production import (worms sqlite + auction backup)
  clean-vectors {auctions|taxa|all}  truncate vector tables to free disk space
  backup [path]     pg_dump to backups/<timestamp>.sql.gz
  restore <file>    restore from backup (DESTRUCTIVE)

${C_HEAD}Tasks (requires ADMIN_USERNAME + ADMIN_PASSWORD env):${C_END}
  scrape [N]        trigger auction scraper (default N=50)
  images [N]        trigger image downloader (default N=20)

${C_HEAD}Testing:${C_END}
  test              end-to-end smoke test (register/me/search)

${C_HEAD}Examples:${C_END}
  ./dev up
  ./dev logs celery-worker
  ./dev psql -c "SELECT COUNT(*) FROM auctions"
  ADMIN_USERNAME=admin ADMIN_PASSWORD=xxx ./dev scrape 100
EOF
}

# ─── dispatch ───────────────────────────────────────────────
cmd="${1:-help}"; shift || true
case "$cmd" in
  up)       cmd_up "$@" ;;
  down)     cmd_down "$@" ;;
  nuke)     cmd_nuke "$@" ;;
  rebuild)  cmd_rebuild "$@" ;;
  restart)  cmd_restart "$@" ;;
  logs)     cmd_logs "$@" ;;
  status|ps) cmd_status "$@" ;;
  psql)     cmd_psql "$@" ;;
  redis)    cmd_redis "$@" ;;
  shell|sh) cmd_shell "$@" ;;
  seed)     cmd_seed "$@" ;;
  worms-import)   cmd_worms_import "$@" ;;
  prod-import)    cmd_prod_import "$@" ;;
  clean-vectors)  cmd_clean_vectors "$@" ;;
  scrape)   cmd_scrape "$@" ;;
  images)   cmd_images "$@" ;;
  test)     cmd_test "$@" ;;
  backup)   cmd_backup "$@" ;;
  restore)  cmd_restore "$@" ;;
  # production
  prod-up)        cmd_prod_up "$@" ;;
  prod-build)     cmd_prod_build "$@" ;;
  prod-down)      cmd_prod_down "$@" ;;
  prod-nuke)      cmd_prod_nuke "$@" ;;
  prod-restart)   cmd_prod_restart "$@" ;;
  prod-logs)      cmd_prod_logs "$@" ;;
  prod-status|prod-ps) cmd_prod_status "$@" ;;
  prod-secrets)   cmd_prod_secrets "$@" ;;
  help|-h|--help) cmd_help ;;
  *) err "unknown command: $cmd"; cmd_help; exit 1 ;;
esac
