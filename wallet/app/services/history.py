"""Transaction history queries with filters."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..db.models import Asset, Chain, Transaction, TxType, User


@dataclass
class HistoryFilter:
    user_id: int
    chain: Chain | None = None
    asset: Asset | None = None
    tx_type: TxType | None = None
    date_from: datetime | None = None
    date_to: datetime | None = None
    limit: int = 100
    offset: int = 0


async def list_transactions(session: AsyncSession, f: HistoryFilter) -> list[Transaction]:
    q = select(Transaction).where(Transaction.user_id == f.user_id)
    if f.chain:
        q = q.where(Transaction.chain == f.chain)
    if f.asset:
        q = q.where(Transaction.asset == f.asset)
    if f.tx_type:
        q = q.where(Transaction.type == f.tx_type)
    if f.date_from:
        q = q.where(Transaction.created_at >= f.date_from)
    if f.date_to:
        q = q.where(Transaction.created_at <= f.date_to)
    q = q.order_by(Transaction.created_at.desc()).limit(f.limit).offset(f.offset)
    res = await session.execute(q)
    return list(res.scalars().all())


async def aggregate_by_asset(session: AsyncSession, user: User, f: HistoryFilter) -> dict:
    """Sum inflow / outflow per asset for a period (used in statements)."""
    txs = await list_transactions(session, f)
    out: dict[str, dict] = {}
    for tx in txs:
        key = f"{tx.chain.value}:{tx.asset.value}"
        bucket = out.setdefault(key, {"in": 0, "out": 0, "count": 0})
        bucket["count"] += 1
        if tx.type in (TxType.DEPOSIT, TxType.INTERNAL_IN):
            bucket["in"] += float(tx.amount)
        elif tx.type in (TxType.WITHDRAW, TxType.INTERNAL_OUT, TxType.FEE):
            bucket["out"] += float(tx.amount)
    return out
