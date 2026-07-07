from __future__ import annotations

from app.core import secret_store
from app.core.secret_store import decrypt_secret, encrypt_secret, secret_tail


def test_encrypt_secret_round_trips_plaintext():
    secret_store._fernet.cache_clear()

    encrypted = encrypt_secret("sk-test-123456")

    assert encrypted.startswith("fernet:")
    assert encrypted != "sk-test-123456"
    assert decrypt_secret(encrypted) == "sk-test-123456"


def test_decrypt_secret_keeps_legacy_plaintext():
    assert decrypt_secret("legacy-secret") == "legacy-secret"


def test_secret_tail_uses_decrypted_value():
    encrypted = encrypt_secret("sk-test-abcdef")

    assert secret_tail(encrypted) == "...cdef"
