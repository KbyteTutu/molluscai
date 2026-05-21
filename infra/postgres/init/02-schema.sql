-- ============================================================
-- MalacoAgent: Full Database Schema
-- Corresponds to design.md section 四 (4.1 - 4.5)
-- ============================================================

-- 4.1 Users & Permissions

CREATE TABLE users (
    id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    username          VARCHAR(50) UNIQUE NOT NULL,
    email             VARCHAR(255) UNIQUE NOT NULL,
    password_hash     VARCHAR(255) NOT NULL,
    role              VARCHAR(20) NOT NULL DEFAULT 'user',
    balance           DECIMAL(10,2) DEFAULT 0.00,
    daily_query_limit INT,
    created_at        TIMESTAMPTZ DEFAULT now(),
    is_active         BOOLEAN DEFAULT true
);

CREATE TABLE role_quotas (
    role                  VARCHAR(20) PRIMARY KEY,
    daily_auction_limit   INT NOT NULL,
    daily_rag_limit       INT NOT NULL,
    features              JSONB DEFAULT '{}',
    rate_limit_per_min    INT NOT NULL,
    -- Hourly + AI quotas (added P5). Sentinel -1 = unlimited, 0 = blocked, >0 = limit.
    hourly_ai_limit       INT NOT NULL DEFAULT -1,
    hourly_auction_limit  INT NOT NULL DEFAULT -1,
    hourly_taxa_limit     INT NOT NULL DEFAULT -1,
    daily_ai_limit        INT NOT NULL DEFAULT -1,
    daily_taxa_limit      INT NOT NULL DEFAULT -1
);

INSERT INTO role_quotas (
    role, daily_auction_limit, daily_rag_limit, features, rate_limit_per_min,
    hourly_ai_limit, hourly_auction_limit, hourly_taxa_limit,
    daily_ai_limit, daily_taxa_limit
) VALUES
    ('user',       20,   5,   '{}',                                                     30,  10,  -1, -1,  50, -1),
    ('vip',        200,  50,  '{"export":true,"advanced_filter":true,"batch_query":true}', 120, 100, -1, -1, 500, -1),
    ('doc_admin',  200,  50,  '{"export":true}',                                         120, -1,  -1, -1, -1,  -1),
    ('superadmin', -1,   -1,  '{}',                                                     -1,  -1,  -1, -1, -1,  -1);

CREATE TABLE query_logs (
    id           BIGSERIAL PRIMARY KEY,
    user_id      UUID REFERENCES users(id),
    query_text   TEXT NOT NULL,
    query_type   VARCHAR(20),
    result_count INT,
    cost         DECIMAL(10,4) DEFAULT 0,
    ip_address   INET,
    status_code  SMALLINT DEFAULT 200,
    created_at   TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX idx_query_logs_user_created
    ON query_logs (user_id, created_at DESC) WHERE user_id IS NOT NULL;
CREATE INDEX idx_query_logs_type_created
    ON query_logs (query_type, created_at DESC);

-- 4.2 Auction Data

CREATE TABLE auctions (
    id            SERIAL PRIMARY KEY,
    item_no       INTEGER UNIQUE NOT NULL,
    name          TEXT,
    family        TEXT,
    size          TEXT,
    locality      TEXT,
    note          TEXT,
    seller        TEXT,
    start_price   DECIMAL(10,2),
    final_price   DECIMAL(10,2),
    end_date      DATE,
    buyer         TEXT,
    is_sold       BOOLEAN GENERATED ALWAYS AS (buyer IS NOT NULL AND buyer NOT LIKE '%no Bids%') STORED,
    images_local  TEXT[],
    images_origin TEXT[],
    created_at    TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX idx_auctions_name_trgm ON auctions USING GIN (name gin_trgm_ops);
CREATE INDEX idx_auctions_family ON auctions (family);
CREATE INDEX idx_auctions_end_date ON auctions (end_date);

-- 4.3 Knowledge Base: Documents + Chunks + Vectors

CREATE TABLE documents (
    id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title            TEXT,
    authors          TEXT[],
    year             INTEGER,
    journal          TEXT,
    doi              TEXT,
    abstract         TEXT,
    taxa_mentioned   TEXT[],
    higher_taxa      JSONB,
    geographic_scope TEXT[],
    content_type     VARCHAR(50),
    keywords         TEXT[],
    doc_category     VARCHAR(30) NOT NULL,
    ocr_model        VARCHAR(50),
    llm_model        VARCHAR(50),
    file_path        TEXT,
    total_pages      INTEGER,
    status           VARCHAR(20) DEFAULT 'pending',
    uploaded_by      UUID REFERENCES users(id),
    created_at       TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE text_chunks (
    id          BIGSERIAL PRIMARY KEY,
    doc_id      UUID REFERENCES documents(id) ON DELETE CASCADE,
    page_num    INTEGER,
    section     TEXT,
    content     TEXT NOT NULL,
    embedding   vector(3584),
    taxa        TEXT[],
    chunk_idx   INTEGER,
    created_at  TIMESTAMPTZ DEFAULT now()
);

-- ivfflat/hnsw both limited to 2000 dims; 3584-dim vectors use brute-force search for now
-- CREATE INDEX idx_chunks_embedding ON text_chunks USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

CREATE TABLE image_chunks (
    id          BIGSERIAL PRIMARY KEY,
    doc_id      UUID REFERENCES documents(id) ON DELETE CASCADE,
    page_num    INTEGER,
    image_path  TEXT NOT NULL,
    caption     TEXT,
    figure_type VARCHAR(50),
    taxa        TEXT[],
    embedding   vector(3584),
    created_at  TIMESTAMPTZ DEFAULT now()
);

-- CREATE INDEX idx_images_embedding ON image_chunks USING ivfflat (embedding vector_cosine_ops) WITH (lists = 50);

-- 4.4 Billing System

CREATE TABLE billing_records (
    id            BIGSERIAL PRIMARY KEY,
    user_id       UUID REFERENCES users(id),
    amount        DECIMAL(10,4) NOT NULL,
    action_type   VARCHAR(30),
    description   TEXT,
    balance_after DECIMAL(10,2),
    created_at    TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE pricing_rules (
    id          SERIAL PRIMARY KEY,
    action_type VARCHAR(30) UNIQUE NOT NULL,
    price       DECIMAL(10,4) NOT NULL,
    free_quota  INTEGER DEFAULT 0,
    vip_price   DECIMAL(10,4),
    is_active   BOOLEAN DEFAULT true
);

-- 4.5 Model API Configuration & Usage

CREATE TABLE model_configs (
    id           SERIAL PRIMARY KEY,
    model_name   VARCHAR(100) UNIQUE NOT NULL,
    provider     VARCHAR(50) NOT NULL,
    api_key      TEXT NOT NULL,
    base_url     TEXT,
    model_id     VARCHAR(100),
    purpose      VARCHAR(30) NOT NULL,
    price_input  DECIMAL(10,6),
    price_output DECIMAL(10,6),
    price_unit   VARCHAR(20) DEFAULT 'per_1k_tokens',
    is_active    BOOLEAN DEFAULT true,
    created_at   TIMESTAMPTZ DEFAULT now(),
    updated_by   UUID REFERENCES users(id)
);

CREATE TABLE model_usage_logs (
    id              BIGSERIAL PRIMARY KEY,
    model_config_id INT REFERENCES model_configs(id) ON DELETE SET NULL,
    model_name      VARCHAR(100) NOT NULL,
    purpose         VARCHAR(30) NOT NULL,
    doc_id          UUID REFERENCES documents(id) ON DELETE SET NULL,
    user_id         UUID REFERENCES users(id),
    input_tokens    INTEGER,
    output_tokens   INTEGER,
    input_pages     INTEGER,
    input_images    INTEGER,
    cost            DECIMAL(10,6) NOT NULL,
    latency_ms      INTEGER,
    status          VARCHAR(20) DEFAULT 'success',
    error_message   TEXT,
    created_at      TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX idx_usage_model ON model_usage_logs (model_name, created_at);
CREATE INDEX idx_usage_doc ON model_usage_logs (doc_id);
CREATE INDEX idx_usage_user ON model_usage_logs (user_id, created_at);

-- 5.7 Security: Captcha & Security Events

CREATE TABLE captcha_sessions (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id     UUID REFERENCES users(id),
    answer      VARCHAR(10) NOT NULL,
    created_at  TIMESTAMPTZ DEFAULT now(),
    expires_at  TIMESTAMPTZ NOT NULL,
    verified    BOOLEAN DEFAULT false
);

CREATE TABLE security_events (
    id          BIGSERIAL PRIMARY KEY,
    user_id     UUID REFERENCES users(id),
    event_type  VARCHAR(30) NOT NULL,
    ip_address  INET,
    user_agent  TEXT,
    detail      JSONB,
    created_at  TIMESTAMPTZ DEFAULT now()
);

-- 5.8 User feedback

CREATE TABLE feedbacks (
    id          BIGSERIAL PRIMARY KEY,
    user_id     UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    category    VARCHAR(20) NOT NULL,
    content     TEXT NOT NULL,
    status      VARCHAR(20) NOT NULL DEFAULT 'open',
    admin_note  TEXT,
    ip_address  INET,
    user_agent  TEXT,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_feedbacks_user_created ON feedbacks (user_id, created_at DESC);
CREATE INDEX idx_feedbacks_status_created ON feedbacks (status, created_at DESC);
