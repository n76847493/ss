"""PDF / CSV statement smoke tests."""
from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

from app.db.models import (
    Asset,
    Chain,
    Transaction,
    TxStatus,
    TxType,
    User,
)
from app.services.history import HistoryFilter
from app.services.statement import build_csv, build_pdf


def _fake_user() -> User:
    u = User(id=1, telegram_id=42, username="alice", first_name="Alice")
    u.created_at = datetime.now(UTC)
    return u


def _fake_txs() -> list[Transaction]:
    txs = []
    for i in range(3):
        t = Transaction(
            id=i + 1,
            user_id=1,
            type=TxType.DEPOSIT if i % 2 == 0 else TxType.WITHDRAW,
            status=TxStatus.CONFIRMED,
            chain=Chain.BTC if i == 0 else Chain.TRON,
            asset=Asset.BTC if i == 0 else Asset.USDT,
            amount=Decimal("0.5") * (i + 1),
            fee=Decimal("0"),
            address_to="bc1qcr8te4kr609gcawutmrza0j4xv80jy8z306fyu",
            txid="a" * 64,
        )
        t.confirmations = 6
        t.created_at = datetime.now(UTC)
        txs.append(t)
    return txs


def test_build_csv() -> None:
    data = build_csv(_fake_user(), _fake_txs(), HistoryFilter(user_id=1))
    text = data.decode()
    assert "Statement for user 42" in text
    assert "DEPOSIT" in text and "WITHDRAW" in text
    assert "USDT" in text and "BTC" in text


def test_build_pdf() -> None:
    data = build_pdf(_fake_user(), _fake_txs(), HistoryFilter(user_id=1))
    # PDF magic header
    assert data[:4] == b"%PDF"
    assert len(data) > 1000
