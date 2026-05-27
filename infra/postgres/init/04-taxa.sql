-- ============================================================
-- Taxa schema: WoRMS / MarineSpecies taxonomy mirror + xlsx backfill.
--
-- One row per taxon keyed by AphiaID (integer). Stores the full WoRMS
-- AphiaRecord shape plus side tables for synonyms, vernaculars, sources,
-- and distributions. A raw JSONB column preserves the original payload.
--
-- Sources tracked by `data_source` column:
--   'worms'  — pulled via REST from marinespecies.org
--   'xlsx'   — backfilled from legacy/Mollusca_species.xlsx (flat, no sub-tables)
--   'merged' — both
--
-- Designed for:
--   * exact + prefix + trigram fuzzy name search (pg_trgm)
--   * parent/child tree walks (parent_aphia_id self-FK, not enforced)
--   * resolve unaccepted → accepted (valid_aphia_id)
--   * vector ANN search for semantic queries (separate table, P3)
-- ============================================================

CREATE TABLE IF NOT EXISTS taxa (
    aphia_id            INTEGER PRIMARY KEY,
    scientificname      TEXT NOT NULL,
    authority           TEXT,
    rank                TEXT,
    rank_id             INTEGER,
    status              TEXT,
    unaccept_reason     TEXT,
    valid_aphia_id      INTEGER,
    valid_name          TEXT,
    valid_authority     TEXT,
    parent_aphia_id     INTEGER,
    original_name_usage_id INTEGER,

    kingdom             TEXT,
    phylum              TEXT,
    subphylum           TEXT,
    class               TEXT,
    subclass            TEXT,
    infraclass          TEXT,
    superorder          TEXT,
    "order"             TEXT,
    suborder            TEXT,
    infraorder          TEXT,
    superfamily         TEXT,
    family              TEXT,
    genus               TEXT,
    species_epithet     TEXT,

    is_marine           BOOLEAN,
    is_brackish         BOOLEAN,
    is_freshwater       BOOLEAN,
    is_terrestrial      BOOLEAN,
    is_extinct          BOOLEAN,

    citation            TEXT,
    lsid                TEXT,
    url                 TEXT,
    api_modified        TIMESTAMPTZ,

    data_source         TEXT NOT NULL DEFAULT 'xlsx'
        CHECK (data_source IN ('worms','xlsx','merged','manual')),
    last_synced_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    raw                 JSONB,

    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_taxa_sciname_trgm
    ON taxa USING GIN (scientificname gin_trgm_ops);
CREATE INDEX IF NOT EXISTS idx_taxa_sciname_lower
    ON taxa (lower(scientificname));
CREATE INDEX IF NOT EXISTS idx_taxa_genus_species
    ON taxa (genus, species_epithet);
CREATE INDEX IF NOT EXISTS idx_taxa_family        ON taxa (family);
CREATE INDEX IF NOT EXISTS idx_taxa_parent        ON taxa (parent_aphia_id);
CREATE INDEX IF NOT EXISTS idx_taxa_valid         ON taxa (valid_aphia_id);
CREATE INDEX IF NOT EXISTS idx_taxa_rank          ON taxa (rank);
CREATE INDEX IF NOT EXISTS idx_taxa_status        ON taxa (status);
CREATE INDEX IF NOT EXISTS idx_taxa_data_source   ON taxa (data_source);

CREATE TABLE IF NOT EXISTS taxa_synonyms (
    aphia_id            INTEGER NOT NULL REFERENCES taxa(aphia_id) ON DELETE CASCADE,
    synonym_aphia_id    INTEGER NOT NULL,
    scientificname      TEXT NOT NULL,
    authority           TEXT,
    status              TEXT,
    raw                 JSONB,
    PRIMARY KEY (aphia_id, synonym_aphia_id)
);
CREATE INDEX IF NOT EXISTS idx_syn_syn_aphia_id ON taxa_synonyms (synonym_aphia_id);
CREATE INDEX IF NOT EXISTS idx_syn_sciname_trgm ON taxa_synonyms USING GIN (scientificname gin_trgm_ops);

CREATE TABLE IF NOT EXISTS taxa_vernaculars (
    id              BIGSERIAL PRIMARY KEY,
    aphia_id        INTEGER NOT NULL REFERENCES taxa(aphia_id) ON DELETE CASCADE,
    vernacular      TEXT NOT NULL,
    language_code   TEXT,
    raw             JSONB
);
-- add source column to track provenance (inaturalist / manual)
ALTER TABLE taxa_vernaculars ADD COLUMN IF NOT EXISTS source TEXT;

CREATE INDEX IF NOT EXISTS idx_vern_aphia    ON taxa_vernaculars (aphia_id);
CREATE INDEX IF NOT EXISTS idx_vern_lower    ON taxa_vernaculars (lower(vernacular));
CREATE INDEX IF NOT EXISTS idx_vern_trgm     ON taxa_vernaculars USING GIN (vernacular gin_trgm_ops);

CREATE TABLE IF NOT EXISTS taxa_inaturalist (
    aphia_id             INTEGER PRIMARY KEY REFERENCES taxa(aphia_id) ON DELETE CASCADE,
    inat_id              INTEGER,
    found                BOOLEAN NOT NULL DEFAULT TRUE,
    preferred_common_name TEXT,
    observations_count   INTEGER,
    wikipedia_url        TEXT,
    wikipedia_summary    TEXT,
    image_url            TEXT,
    conservation_status  TEXT,
    raw                  JSONB,
    synced_at            TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS taxa_sources (
    id              BIGSERIAL PRIMARY KEY,
    aphia_id        INTEGER NOT NULL REFERENCES taxa(aphia_id) ON DELETE CASCADE,
    source_id       INTEGER,
    use_type        TEXT,
    reference       TEXT,
    page            TEXT,
    url             TEXT,
    link            TEXT,
    doi             TEXT,
    raw             JSONB
);
CREATE INDEX IF NOT EXISTS idx_src_aphia ON taxa_sources (aphia_id);

CREATE TABLE IF NOT EXISTS taxa_distributions (
    id                    BIGSERIAL PRIMARY KEY,
    aphia_id              INTEGER NOT NULL REFERENCES taxa(aphia_id) ON DELETE CASCADE,
    locality              TEXT,
    locality_id           TEXT,
    higher_geography      TEXT,
    higher_geography_id   TEXT,
    establishment_means   TEXT,
    decimal_latitude      DOUBLE PRECISION,
    decimal_longitude     DOUBLE PRECISION,
    quality_status        TEXT,
    raw                   JSONB
);
CREATE INDEX IF NOT EXISTS idx_dist_aphia ON taxa_distributions (aphia_id);

-- Embeddings live in their own table so the same AphiaID can have multiple
-- embeddings across different models / dimensions. Kept optional for P3.
-- pgvector ivfflat/hnsw indexes cap at 2000 dims. If we use a 3584-dim
-- model later, either switch to halfvec or create a dedicated table with
-- halfvec(3584). For now allow any dim via vector without an ANN index.
CREATE TABLE IF NOT EXISTS taxa_embeddings (
    id              BIGSERIAL PRIMARY KEY,
    aphia_id        INTEGER NOT NULL REFERENCES taxa(aphia_id) ON DELETE CASCADE,
    model_name      TEXT NOT NULL,
    dim             INTEGER NOT NULL,
    embedding       vector,
    text_hash       TEXT NOT NULL,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (aphia_id, model_name, text_hash)
);
CREATE INDEX IF NOT EXISTS idx_embed_aphia ON taxa_embeddings (aphia_id);

CREATE OR REPLACE FUNCTION set_updated_at() RETURNS trigger AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_taxa_updated_at ON taxa;
CREATE TRIGGER trg_taxa_updated_at
    BEFORE UPDATE ON taxa
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();
