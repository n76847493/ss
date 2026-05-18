"""TOTP utility smoke test (no DB)."""
from __future__ import annotations

import pyotp

from app.db.models import User
from app.services.twofa import make_qr_png, totp_uri, verify_code


def test_qr_and_verify() -> None:
    u = User(id=1, telegram_id=1, totp_secret=pyotp.random_base32(), totp_enabled=True)
    uri = totp_uri(u, issuer="UnitTest")
    assert uri.startswith("otpauth://totp/")
    png = make_qr_png(uri)
    assert png[:8] == b"\x89PNG\r\n\x1a\n"

    code = pyotp.TOTP(u.totp_secret).now()
    assert verify_code(u, code) is True
    assert verify_code(u, "000000") is False
