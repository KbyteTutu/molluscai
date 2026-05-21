# WoRMS / MarineSpecies dump script

Standalone single-file scraper that walks a WoRMS AphiaID subtree and writes a
self-contained SQLite database. Designed to run on **any host with fast access
to https://www.marinespecies.org/** (the production app is in China, where
that endpoint is slow), then ship the gzipped output back home.

## What it grabs

For every taxon under the root AphiaID:

| Endpoint | Stored in |
|---|---|
| `AphiaRecordByAphiaID/{id}` | `taxa` (incl. `original_aphia_id`, `valid_name`, `unaccept_reason`) |
| `AphiaSynonymsByAphiaID/{id}` | `synonyms` |
| `AphiaVernacularsByAphiaID/{id}` | `vernaculars` |
| `AphiaSourcesByAphiaID/{id}` | `sources` (incl. `fulltext`) |
| `AphiaDistributionsByAphiaID/{id}` | `distributions` |
| `AphiaClassificationByAphiaID/{id}` | `classification` (full hierarchy with all rank levels) |
| `AphiaChildrenByAphiaID/{id}` | `children` (denormalized parent→child list) **+** drives `frontier` |
| `AphiaAttributesByAphiaID/{id}` | `attributes` (traits/measurements, recursive children flattened) |
| `AphiaExternalIDByAphiaID/{id}?type=…` × 10 sources | `external_ids` (NCBI, BOLD, TSN, LSID, IUCN, FishBase, AlgaeBase, Dyntaxa, Plazi, OPAC) |

Plus a `frontier` table for resumable BFS state and a `meta` table for run metadata.

Each row's full original API JSON is mirrored in a `raw` column — future fields require no rescrape, just reparse.

## Setup (on the overseas host)

```bash
git clone <this-repo>          # or just scp the two files in this folder
cd scripts/worms
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
```

Python 3.10+ required.

## Run

Full Mollusca subtree (root AphiaID = 51, ≈ 120k taxa, expect 4–24 h depending on RTT and concurrency):

```bash
python3 worms_dump.py --root 51 --out worms_mollusca.sqlite --gzip
```

Small smoke test (Polyplacophora ≈ 1.5k taxa, finishes in minutes):

```bash
python3 worms_dump.py --root 55 --out worms_polyplacophora.sqlite --gzip
```

Resume after Ctrl-C / crash / network drop:

```bash
python3 worms_dump.py --root 51 --out worms_mollusca.sqlite      # same --out path
```

The `frontier` table records every visited AphiaID. Restarting picks up
exactly where it stopped — anything that was in flight is requeued
automatically.

## Tuning

| Flag | Default | Notes |
|---|---|---|
| `--concurrency N` | 16 | Max in-flight taxa. Each consumes ~17 API calls in parallel internally, so effective HTTP concurrency ≈ 17N. Be polite. |
| `--min-interval SEC` | 0.1 | Global min spacing between any two HTTP requests. Set to `0.2` if you start seeing 429/503. |
| `--max-depth N` | 99 | Limit BFS depth from `--root`. Use 1 for "direct children only". |
| `--timeout SEC` | 30 | HTTP timeout per request. |
| `--max-retries N` | 5 | Exponential backoff retries on 429/5xx/timeout. |
| `--gzip` | off | Compress the SQLite file when done. |

## Ship the data home

```bash
scp worms_mollusca.sqlite.gz user@home:/path/to/molluscai/data_import/
```

Then on the home machine, with the stack running (`./dev up`):

```bash
./dev worms-import data_import/worms_mollusca.sqlite.gz
```

The importer is **idempotent**: re-running it overwrites WoRMS-sourced fields
on existing rows while preserving xlsx-only fields (subphylum, subclass, etc.),
and flips `data_source` from `xlsx` → `merged` on rows that already had local
data. Synonyms / vernaculars / distributions / classification / children /
attributes / external IDs are fully replaced.

For a full production import that also restores the `auctions` table from
a `postgres_backup.sql` dump, use:

```bash
./dev prod-import data_import/worms_mollusca.sqlite.gz \
                  data_import/postgres_backup.sql
```

Either argument can be omitted (or empty string) to skip that half of the
import.

## Attribution (required)

When displaying WoRMS-derived data, attribute:

> WoRMS Editorial Board. World Register of Marine Species.
> Available from https://www.marinespecies.org at VLIZ.

Each `taxa` row already carries WoRMS' own per-record citation string in
the `citation` column — surface it on detail pages.

## Layout of the output SQLite

```sql
-- Inspect quickly:
sqlite3 worms_mollusca.sqlite "
  SELECT 'taxa', COUNT(*) FROM taxa
  UNION ALL SELECT 'synonyms', COUNT(*) FROM synonyms
  UNION ALL SELECT 'vernaculars', COUNT(*) FROM vernaculars
  UNION ALL SELECT 'sources', COUNT(*) FROM sources
  UNION ALL SELECT 'distributions', COUNT(*) FROM distributions
  UNION ALL SELECT 'frontier.done', COUNT(*) FROM frontier WHERE state='done'
  UNION ALL SELECT 'frontier.failed', COUNT(*) FROM frontier WHERE state='failed';
"
```

The `raw` columns hold the original API JSON unchanged — future fields
won't require re-scraping, just re-parsing.
