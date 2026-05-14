-- ============================================================
-- Semantic search layer for taxa.
--
-- One halfvec per taxon per active embedding model.
-- halfvec + HNSW supports up to 2000 dims in pgvector 0.8.
-- Qwen3-Embedding-8B emits 4096 dims natively but supports MRL
-- (Matryoshka) truncation; we store the first 2000 dims with
-- negligible quality loss. Shorter-dim models are zero-padded to 2000.
-- text_hash lets us skip re-embedding rows whose composite text is unchanged.
-- ============================================================

DROP TABLE IF EXISTS taxa_embeddings;

CREATE TABLE taxa_embeddings (
    aphia_id     INTEGER NOT NULL REFERENCES taxa(aphia_id) ON DELETE CASCADE,
    model_name   TEXT NOT NULL,
    dim          INTEGER NOT NULL,
    embedding    halfvec(2000) NOT NULL,
    text_hash    TEXT NOT NULL,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (aphia_id, model_name)
);

CREATE INDEX idx_taxa_emb_model ON taxa_embeddings (model_name);

CREATE INDEX idx_taxa_emb_hnsw
    ON taxa_embeddings
    USING hnsw (embedding halfvec_cosine_ops)
    WITH (m = 16, ef_construction = 64);
