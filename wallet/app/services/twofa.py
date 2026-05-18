"""TOTP-based two-factor authentication."""
from __future__ import annotations

import io

import pyotp
import qrcode
from sqlalchemy.ext.asyncio import AsyncSession

from ..db.models import AuditLog, User


async def setup_totp(session: AsyncSession, user: User, *, issuer: str = "WalletBot") -> str:
    secret = pyotp.random_base32()
    user.totp_secret = secret
    user.totp_enabled = False
    session.add(AuditLog(user_id=user.id, event="totp_setup_started"))
    return secret


def totp_uri(user: User, issuer: str = "WalletBot") -> str:
    if not user.totp_secret:
        return ""
    return pyotp.TOTP(user.totp_secret).provisioning_uri(
        name=str(user.telegram_id), issuer_name=issuer
    )


def make_qr_png(uri: str) -> bytes:
    img = qrcode.make(uri)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


async def verify_and_enable(session: AsyncSession, user: User, code: str) -> bool:
    if not user.totp_secret:
        return False
    ok = pyotp.TOTP(user.totp_secret).verify(code, valid_window=1)
    if ok:
        user.totp_enabled = True
        session.add(AuditLog(user_id=user.id, event="totp_enabled"))
    return ok


def verify_code(user: User, code: str) -> bool:
    if not user.totp_enabled or not user.totp_secret:
        return False
    return pyotp.TOTP(user.totp_secret).verify(code, valid_window=1)


async def disable_totp(session: AsyncSession, user: User) -> None:
    user.totp_secret = None
    user.totp_enabled = False
    session.add(AuditLog(user_id=user.id, event="totp_disabled"))
