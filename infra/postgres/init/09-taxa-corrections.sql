-- 9. Information Corrections (user-submitted, admin-reviewed)

CREATE TABLE IF NOT EXISTS corrections (
    id               BIGSERIAL PRIMARY KEY,
    user_id          UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    target_type      VARCHAR(50) NOT NULL,
    target_id        VARCHAR(100) NOT NULL,
    target_title     VARCHAR(500),
    field_name       VARCHAR(100) NOT NULL,
    current_value    TEXT,
    suggested_value  TEXT NOT NULL,
    note             TEXT,
    status           VARCHAR(20) NOT NULL DEFAULT 'pending',
    admin_note       TEXT,
    ip_address       INET,
    user_agent       TEXT,
    created_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at       TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_corrections_user_created ON corrections (user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_corrections_status_created ON corrections (status, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_corrections_target ON corrections (target_type, target_id);
