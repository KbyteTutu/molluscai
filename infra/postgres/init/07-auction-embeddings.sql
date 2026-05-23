-- ============================================================
-- Semantic search layer for auction listings.
--
-- One halfvec per auction item per active embedding model.
-- halfvec + HNSW supports up to 2000 dims in pgvector 0.8.
-- Qwen3-Embedding-8B emits 4096 dims natively but supports MRL
-- (Matryoshka) truncation; we store the first 2000 dims with
-- negligible quality loss. Shorter-dim models are zero-padded to 2000.
-- text_hash lets us skip re-embedding rows whose composite text is unchanged.
-- ============================================================

DROP TABLE IF EXISTS auction_embeddings;

CREATE TABLE auction_embeddings (
    item_no      INTEGER NOT NULL REFERENCES auctions(item_no) ON DELETE CASCADE,
    model_name   TEXT NOT NULL,
    dim          INTEGER NOT NULL,
    embedding    halfvec(2000) NOT NULL,
    text_hash    TEXT NOT NULL,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (item_no, model_name)
);

CREATE INDEX idx_auction_emb_model ON auction_embeddings (model_name);

CREATE INDEX idx_auction_emb_hnsw
    ON auction_embeddings
    USING hnsw (embedding halfvec_cosine_ops)
    WITH (m = 16, ef_construction = 64);
