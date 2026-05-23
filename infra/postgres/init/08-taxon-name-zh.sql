CREATE TABLE IF NOT EXISTS taxon_name_zh (
    latin_name   TEXT PRIMARY KEY,
    chinese_name TEXT NOT NULL,
    rank_type    TEXT NOT NULL
);

CREATE INDEX idx_taxon_name_zh_rank ON taxon_name_zh (rank_type);
