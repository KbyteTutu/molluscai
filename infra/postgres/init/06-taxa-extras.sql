-- ============================================================
-- Taxa extras: WoRMS classification / children / attributes /
-- external IDs. Companion to 04-taxa.sql.
--
-- All statements use IF NOT EXISTS so this file is safe to apply
-- to existing databases that already ran 04-taxa.sql.
-- ============================================================

-- ─── classification ─────────────────────────────────────────
-- One row per (aphia_id, ancestor) pair. depth=0 is self,
-- depth=N is the Nth ancestor up. ~13x the size of taxa
-- (each species has its full Linnaean chain).
CREATE TABLE IF NOT EXISTS taxa_classification (
    aphia_id            INTEGER NOT NULL REFERENCES taxa(aphia_id) ON DELETE CASCADE,
    ancestor_aphia_id   INTEGER NOT NULL,
    rank                TEXT,
    scientificname      TEXT NOT NULL,
    depth               INTEGER NOT NULL,
    PRIMARY KEY (aphia_id, ancestor_aphia_id)
);
CREATE INDEX IF NOT EXISTS idx_cls_ancestor ON taxa_classification (ancestor_aphia_id);
CREATE INDEX IF NOT EXISTS idx_cls_depth    ON taxa_classification (aphia_id, depth);

-- ─── children ───────────────────────────────────────────────
-- Direct parent->child mapping. Useful for tree expansion in UI
-- without recursive CTEs over taxa.parent_aphia_id.
CREATE TABLE IF NOT EXISTS taxa_children (
    parent_aphia_id     INTEGER NOT NULL REFERENCES taxa(aphia_id) ON DELETE CASCADE,
    child_aphia_id      INTEGER NOT NULL,
    rank                TEXT,
    scientificname      TEXT,
    status              TEXT,
    PRIMARY KEY (parent_aphia_id, child_aphia_id)
);
CREATE INDEX IF NOT EXISTS idx_chld_child  ON taxa_children (child_aphia_id);
CREATE INDEX IF NOT EXISTS idx_chld_status ON taxa_children (parent_aphia_id, status);

-- ─── attributes ─────────────────────────────────────────────
-- Trait/measurement records. Includes inherited attributes
-- (aphia_id_inherited) so a species without its own row may
-- still surface ancestor traits.
CREATE TABLE IF NOT EXISTS taxa_attributes (
    id                      BIGSERIAL PRIMARY KEY,
    aphia_id                INTEGER NOT NULL REFERENCES taxa(aphia_id) ON DELETE CASCADE,
    measurement_type        TEXT,
    measurement_type_id     INTEGER,
    measurement_value       TEXT,
    category_id             INTEGER,
    aphia_id_inherited      INTEGER,
    quality_status          TEXT,
    source_id               INTEGER,
    reference               TEXT,
    raw                     JSONB
);
CREATE INDEX IF NOT EXISTS idx_attr_aphia ON taxa_attributes (aphia_id);
CREATE INDEX IF NOT EXISTS idx_attr_type  ON taxa_attributes (measurement_type);

-- ─── external_ids ───────────────────────────────────────────
-- Cross-references to other taxonomy databases. A single taxon
-- can have many entries per source (e.g. multiple NCBI tax_ids
-- for synonymous concepts).
CREATE TABLE IF NOT EXISTS taxa_external_ids (
    aphia_id            INTEGER NOT NULL REFERENCES taxa(aphia_id) ON DELETE CASCADE,
    source              TEXT NOT NULL,
    external_id         TEXT NOT NULL,
    PRIMARY KEY (aphia_id, source, external_id)
);
CREATE INDEX IF NOT EXISTS idx_extid_source ON taxa_external_ids (source, external_id);

-- ─── reinforce fuzzy search indexes ─────────────────────────
-- 04-taxa.sql already creates trigram indexes on scientificname
-- and synonyms. Repeat with IF NOT EXISTS so this file is safe
-- to run standalone on legacy databases.
CREATE INDEX IF NOT EXISTS idx_taxa_sciname_trgm
    ON taxa USING GIN (scientificname gin_trgm_ops);
CREATE INDEX IF NOT EXISTS idx_syn_sciname_trgm
    ON taxa_synonyms USING GIN (scientificname gin_trgm_ops);
CREATE INDEX IF NOT EXISTS idx_vern_trgm
    ON taxa_vernaculars USING GIN (vernacular gin_trgm_ops);

-- Lower-case prefix indexes for exact/prefix lookups that the
-- planner picks up via lower(col) LIKE 'foo%'.
CREATE INDEX IF NOT EXISTS idx_taxa_sciname_lower
    ON taxa (lower(scientificname));
CREATE INDEX IF NOT EXISTS idx_syn_sciname_lower
    ON taxa_synonyms (lower(scientificname));
CREATE INDEX IF NOT EXISTS idx_vern_lower
    ON taxa_vernaculars (lower(vernacular));
