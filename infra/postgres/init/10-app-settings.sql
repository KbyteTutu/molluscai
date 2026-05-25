CREATE TABLE IF NOT EXISTS app_settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT now()
);
INSERT INTO app_settings (key, value) VALUES
    ('smart_search_auction', 'false'),
    ('smart_search_taxa', 'true'),
    ('smart_search_documents', 'false')
ON CONFLICT (key) DO NOTHING;
