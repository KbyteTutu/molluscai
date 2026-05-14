-- ============================================================
-- Bootstrap built-in superadmin account.
-- Hardcoded TESTING credentials — change before any non-local deployment.
--   username: kbytetutu
--   password: Tu1994125
-- The password_hash below is bcrypt(Tu1994125) generated with the
-- same passlib settings the backend uses.
-- Idempotent: re-running upserts the account (UPDATE on conflict).
-- ============================================================

INSERT INTO users (username, email, password_hash, role, is_active)
VALUES (
    'kbytetutu',
    'kbytetutu@malacoagent.local',
    '$2b$12$LIy8jSDPxs9iutT4JLawEuOHf/.bjv5teyCUWSVlxItbyPfKYG/Sa',
    'superadmin',
    true
)
ON CONFLICT (username) DO UPDATE SET
    password_hash = EXCLUDED.password_hash,
    role          = 'superadmin',
    is_active     = true;
