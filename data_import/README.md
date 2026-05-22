# data_import/

Drop production data dumps here. **None of the data files are tracked by git** — they are large binary blobs (the WoRMS SQLite is ≈1.9 GB, the Postgres dump is ≈700 MB). Only this README is tracked.

## Expected files

| File | Source | Size | Purpose |
|---|---|---|---|
| `worms_mollusca.sqlite` | `scripts/worms/worms_dump.py` (run on overseas host) | ≈1.9 GB | Full WoRMS Mollusca taxonomy mirror — 315k taxa, 195k synonyms, 20k vernaculars, 174k distributions, 4M classification rows. Source for species search. |
| `postgres_backup.sql` | `pg_dump` of legacy ShellAuction database | ≈700 MB | Legacy auction data import. Re-uses staging→insert flow. |

Either file may also appear gzipped (`.sqlite.gz` / `.sql.gz`) — the import scripts accept both transparently.

## How to import

### Both at once (production one-shot)

```bash
bash scripts/prod_import.sh data_import/worms_mollusca.sqlite data_import/postgres_backup.sql
```

### Individually

```bash
# WoRMS taxonomy → taxa / taxa_synonyms / taxa_vernaculars / taxa_classification / ...
./dev worms-import data_import/worms_mollusca.sqlite

# Legacy auctions
./dev seed   # uses legacy/postgres_backup.sql by default; see scripts/dev.sh
```

> Both `worms-import` and `prod-import` go through `scripts/prod_import.sh`,
> which `docker cp`'s the file into the backend container. The repository's
> `data_import/` directory is **not** volume-mounted into the container, so
> `docker compose exec backend python -m scripts.import_worms_sqlite ...`
> directly will fail with `FileNotFoundError`. Always use the wrapper.

The WoRMS importer:
- Auto-creates any missing extras tables (classification / children / attributes / external_ids) on first run.
- Is **idempotent** — safe to re-run after partial failures or for incremental updates.
- Runs `ANALYZE` at the end so query planner picks up the new statistics.
- Supports `.sqlite` and `.sqlite.gz` input.

## Why these files are git-ignored

1. **Size**: GitHub limits individual files to 100 MB. `git-lfs` would work but adds bandwidth cost and operational overhead.
2. **Provenance**: WoRMS data is licensed CC-BY-4.0 and must carry per-record attribution — we mirror it at import time, no need to redistribute the dump.
3. **Reproducibility**: The dump can always be regenerated with `scripts/worms/worms_dump.py` (takes 4–24 h depending on RTT).

See `.gitignore` for the exact patterns.
