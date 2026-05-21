#!/usr/bin/env bash
# Production data import driver.
#
# Imports two source files into a running mollusc-postgres container:
#   * worms_mollusca.sqlite (or .gz) -> taxa.* tables    (via backend python module)
#   * postgres_backup.sql            -> auctions table  (staging -> upsert)
#
# Both arguments are optional. If only one is supplied, only that import runs.
#
# Usage:
#   bash scripts/prod_import.sh [WORMS_SQLITE] [POSTGRES_BACKUP_SQL]
#
# Examples:
#   bash scripts/prod_import.sh data_import/worms_mollusca.sqlite \
#                               data_import/postgres_backup.sql
#   bash scripts/prod_import.sh data_import/worms_mollusca.sqlite.gz
#   bash scripts/prod_import.sh "" data_import/postgres_backup.sql
#
# Environment overrides:
#   PG_CONTAINER       (default: mollusc-postgres)
#   BACKEND_CONTAINER  (default: mollusc-backend)
#   POSTGRES_USER      (default: mollusc)
#   POSTGRES_DB        (default: molluscai)

set -euo pipefail

SCRIPT_PATH="$(readlink -f "${BASH_SOURCE[0]}")"
ROOT="$(cd "$(dirname "$SCRIPT_PATH")/.." && pwd)"
cd "$ROOT"

PG_CONTAINER="${PG_CONTAINER:-mollusc-postgres}"
BACKEND_CONTAINER="${BACKEND_CONTAINER:-mollusc-backend}"
PG_USER="${POSTGRES_USER:-mollusc}"
PG_DB="${POSTGRES_DB:-molluscai}"

WORMS_INPUT="${1:-}"
BACKUP_INPUT="${2:-}"

# ─── colors ─────────────────────────────────────────────────
if [[ -t 1 ]]; then
  C_OK=$'\e[32m'; C_ERR=$'\e[31m'; C_WARN=$'\e[33m'
  C_HEAD=$'\e[1;36m'; C_END=$'\e[0m'
else
  C_OK=''; C_ERR=''; C_WARN=''; C_HEAD=''; C_END=''
fi
log()  { printf '%s==>%s %s\n' "$C_HEAD" "$C_END" "$*"; }
ok()   { printf '%s✓%s %s\n'  "$C_OK"   "$C_END" "$*"; }
warn() { printf '%s!%s %s\n'  "$C_WARN" "$C_END" "$*"; }
err()  { printf '%s✗%s %s\n'  "$C_ERR"  "$C_END" "$*" >&2; }
die()  { err "$*"; exit 1; }

container_running() { docker ps --format '{{.Names}}' | grep -qx "$1"; }

require_container() {
  container_running "$1" || die "$1 is not running. Start the stack first (./dev up)."
}

# ─── WoRMS importer ─────────────────────────────────────────
import_worms() {
  local host_path="$1"
  [[ -f "$host_path" ]] || die "WoRMS input not found: $host_path"
  require_container "$BACKEND_CONTAINER"

  log "copying $host_path into $BACKEND_CONTAINER:/tmp/worms.sqlite ..."
  local in_container_name
  case "$host_path" in
    *.gz) in_container_name="/tmp/worms.sqlite.gz" ;;
    *)    in_container_name="/tmp/worms.sqlite" ;;
  esac
  docker cp "$host_path" "$BACKEND_CONTAINER:$in_container_name"

  log "running python importer (this can take 10-30 min for full Mollusca dump) ..."
  docker exec -t "$BACKEND_CONTAINER" \
    python -m scripts.import_worms_sqlite "$in_container_name"

  docker exec "$BACKEND_CONTAINER" rm -f "$in_container_name" || true
  ok "WoRMS import complete"
}

# ─── auction backup importer (mirrors dev.sh:cmd_seed) ─────
import_auction_backup() {
  local host_path="$1"
  [[ -f "$host_path" ]] || die "Auction backup not found: $host_path"
  require_container "$PG_CONTAINER"

  local existing
  existing=$(docker exec "$PG_CONTAINER" psql -U "$PG_USER" -d "$PG_DB" -tAc \
              "SELECT COUNT(*) FROM auctions" 2>/dev/null || echo 0)
  if [[ "$existing" -gt 100 ]]; then
    warn "auctions table already has $existing rows."
    if [[ -t 0 ]]; then
      printf "Continue (re-importing into populated table is safe — uses ON CONFLICT DO NOTHING)? [y/N] "
      read -r c
      [[ "$c" == "y" || "$c" == "Y" ]] || die "aborted"
    else
      log "non-interactive shell, proceeding"
    fi
  fi

  local sql_in_container="/tmp/postgres_backup.sql"
  case "$host_path" in
    *.gz)
      log "decompressing $host_path -> container ..."
      gunzip -c "$host_path" | docker exec -i "$PG_CONTAINER" \
        sh -c "cat > $sql_in_container"
      ;;
    *)
      log "copying $host_path into $PG_CONTAINER ..."
      docker cp "$host_path" "$PG_CONTAINER:$sql_in_container"
      ;;
  esac

  log "preparing staging table ..."
  docker exec "$PG_CONTAINER" psql -U "$PG_USER" -d "$PG_DB" -c "
    DROP TABLE IF EXISTS shellauction_staging;
    CREATE TABLE shellauction_staging (
      id integer, item integer, image text, name text, family text,
      size text, locality text, note text, seller text,
      start_price integer, current_price integer, end_date text,
      owner text, deal_date date
    );" >/dev/null

  log "extracting COPY block ..."
  docker exec "$PG_CONTAINER" bash -c "awk '
    /^COPY public\.shellauction/ {
      print \"COPY shellauction_staging (id, item, image, name, family, size, locality, note, seller, start_price, current_price, end_date, owner, deal_date) FROM stdin;\"; in_copy=1; next
    }
    in_copy && /^\\\\\.\$/ { print; in_copy=0; exit }
    in_copy { print }
  ' $sql_in_container > /tmp/staging_copy.sql"

  log "loading staging data (~30s for full dump) ..."
  docker exec "$PG_CONTAINER" psql -U "$PG_USER" -d "$PG_DB" \
    -f /tmp/staging_copy.sql >/dev/null

  log "transforming staging -> auctions (ON CONFLICT DO NOTHING) ..."
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

  docker exec "$PG_CONTAINER" psql -U "$PG_USER" -d "$PG_DB" \
    -c "DROP TABLE shellauction_staging;" >/dev/null
  docker exec "$PG_CONTAINER" rm -f "$sql_in_container" /tmp/staging_copy.sql

  local final
  final=$(docker exec "$PG_CONTAINER" psql -U "$PG_USER" -d "$PG_DB" -tAc \
            "SELECT COUNT(*) FROM auctions")
  ok "auction backup import complete. auctions=$final"
}

# ─── dispatch ───────────────────────────────────────────────
[[ -z "$WORMS_INPUT" && -z "$BACKUP_INPUT" ]] && die \
  "usage: $0 [WORMS_SQLITE] [POSTGRES_BACKUP_SQL]    (at least one required)"

if [[ -n "$WORMS_INPUT" ]]; then
  log "=== WoRMS taxonomy import: $WORMS_INPUT ==="
  import_worms "$WORMS_INPUT"
  echo
fi

if [[ -n "$BACKUP_INPUT" ]]; then
  log "=== Auction backup import: $BACKUP_INPUT ==="
  import_auction_backup "$BACKUP_INPUT"
  echo
fi

ok "All imports finished"
