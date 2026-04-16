import pytest
from app.security.auth import hash_password, verify_password, create_access_token, create_refresh_token, decode_token


class TestPasswordHashing:
    def test_hash_and_verify(self):
        password = "my-secure-password"
        hashed = hash_password(password)
        assert hashed != password
        assert verify_password(password, hashed)

    def test_wrong_password_fails(self):
        hashed = hash_password("correct-password")
        assert not verify_password("wrong-password", hashed)

    def test_different_hashes_for_same_password(self):
        h1 = hash_password("same-password")
        h2 = hash_password("same-password")
        assert h1 != h2  # Argon2 uses random salt


class TestJWT:
    def test_create_and_decode_access_token(self):
        token = create_access_token(user_id=1, username="admin")
        payload = decode_token(token)
        assert payload["sub"] == "1"
        assert payload["username"] == "admin"
        assert payload["type"] == "access"
        assert "jti" in payload
        assert "exp" in payload

    def test_create_and_decode_refresh_token(self):
        token = create_refresh_token(user_id=42)
        payload = decode_token(token)
        assert payload["sub"] == "42"
        assert payload["type"] == "refresh"

    def test_invalid_token_raises(self):
        with pytest.raises(Exception):
            decode_token("invalid-token-string")


class TestAuditRedaction:
    def test_sensitive_keys_redacted(self):
        from app.services.audit_service import _redact_sensitive

        details = {
            "username": "admin",
            "password": "secret123",
            "api_token": "cf-token-xyz",
            "hostname": "example.com",
        }
        redacted = _redact_sensitive(details)
        assert redacted["username"] == "admin"
        assert redacted["password"] == "***REDACTED***"
        assert redacted["api_token"] == "***REDACTED***"
        assert redacted["hostname"] == "example.com"

    def test_nested_redaction(self):
        from app.services.audit_service import _redact_sensitive

        details = {"config": {"secret_key": "abc", "name": "test"}}
        redacted = _redact_sensitive(details)
        assert redacted["config"]["secret_key"] == "***REDACTED***"
        assert redacted["config"]["name"] == "test"

    def test_none_details(self):
        from app.services.audit_service import _redact_sensitive
        assert _redact_sensitive(None) is None
