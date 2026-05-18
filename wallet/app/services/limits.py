"""Anti-fraud limits."""
from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import get_settings
from ..db.models import Transaction, TxType, User
from .pricing import to_usd


class LimitError(ValueError):
    pass


async def check_withdrawal(
    session: AsyncSession,
    user: User,
    *,
    chain: str,
    asset: str,
    amount: Decimal,
) -> dict:
    s = get_settings()
    usd_value = await to_usd(asset, amount)

    if usd_value > Decimal(s.withdraw_per_tx_limit_usd):
        raise LimitError(
            f"Withdrawal exceeds per-tx limit (${s.withdraw_per_tx_limit_usd:.0f}). Value ≈ ${usd_value:.2f}."
        )

    since = datetime.now(UTC) - timedelta(hours=24)
    res = await session.execute(
        select(Transaction).where(
            Transaction.user_id == user.id,
            Transaction.type == TxType.WITHDRAW,
            Transaction.created_at >= since,
        )
    )
    spent_usd = Decimal(0)
    for tx in res.scalars().all():
        spent_usd += await to_usd(tx.asset.value, Decimal(tx.amount))

    if spent_usd + usd_value > Decimal(s.withdraw_daily_limit_usd):
        raise LimitError(
            f"24h cap reached (${s.withdraw_daily_limit_usd:.0f}). Spent ≈ ${spent_usd:.2f}, requested ≈ ${usd_value:.2f}."
        )

    return {
        "usd_value": usd_value,
        "needs_2fa": usd_value >= Decimal(s.withdraw_require_2fa_over_usd),
    }
