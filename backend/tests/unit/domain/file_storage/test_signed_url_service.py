from datetime import datetime, timedelta

from src.domain.file_storage.signed_url_service import SignedUrlService


class TestSignedUrlService:
    def test_generate_signed_url_with_signature_and_base_url(self):
        svc = SignedUrlService(
            secret_key="secret", base_url="https://api.example/api/v1/downloads/file"
        )
        signed = svc.generate_signed_url(
            token="tok123", ttl_minutes=1, include_signature=True
        )
        assert signed.url.startswith("https://api.example/api/v1/downloads/file/tok123")
        assert signed.signature is not None
        assert signed.get_remaining_seconds() > 0

    def test_generate_download_url_without_signature(self):
        svc = SignedUrlService(
            secret_key="secret", base_url="https://api.example/api/v1/downloads/file"
        )
        url = svc.generate_download_url("tok456", ttl_minutes=1)
        assert url == "https://api.example/api/v1/downloads/file/tok456"

    def test_validate_signature_matches(self):
        svc = SignedUrlService(secret_key="secret", base_url="/api/v1/downloads/file")
        exp = datetime.utcnow() + timedelta(minutes=5)
        sig = svc._generate_signature("tok789", exp)
        assert svc.validate_signature("tok789", sig, exp) is True
        assert svc.validate_signature("tok789", "bad", exp) is False

    def test_validate_token_checks_length_signature_and_expiry(self):
        svc = SignedUrlService(secret_key="secret")
        assert svc.validate_token("short") is False
        exp = datetime.utcnow() + timedelta(minutes=5)
        token = "toktoktoktoktokk"  # 16+ chars
        sig = svc._generate_signature(token, exp)
        assert svc.validate_token(token, signature=sig, expires_at=exp) is True
        assert svc.validate_token(token, signature="bad", expires_at=exp) is False
        past = datetime.utcnow() - timedelta(seconds=1)
        assert svc.validate_token(token, expires_at=past) is False

    # Cloud delegation tests removed
