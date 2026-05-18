"""Off-chain internal transfers between bot users."""
from __future__ import annotations

from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..db.models import (
    Asset,
    AuditLog,
    Chain,
    Transaction,
    TxStatus,
    TxType,
    User,
)
from .wallet import get_balance


async def internal_transfer(
    session: AsyncSession,
    *,
    sender: User,
    recipient_username_or_id: str,
    chain: Chain,
    asset: Asset,
    amount: Decimal,
    note: str | None = None,
) -> tuple[Transaction, Transaction]:
    if amount <= 0:
        raise ValueError("amount must be positive")

    # locate recipient
    query = select(User)
    if recipient_username_or_id.startswith("@"):
        query = query.where(User.username == recipient_username_or_id[1:])
    elif recipient_username_or_id.isdigit():
        query = query.where(User.telegram_id == int(recipient_username_or_id))
    else:
        query = query.where(User.username == recipient_username_or_id)
    res = await session.execute(query)
    recipient = res.scalar_one_or_none()
    if recipient is None or recipient.is_blocked:
        raise ValueError("recipient not found or blocked")
    if recipient.id == sender.id:
        raise ValueError("cannot transfer to yourself")

    sender_bal = await get_balance(session, sender, chain, asset)
    if (sender_bal.amount - sender_bal.locked) < amount:
        raise ValueError("insufficient balance")

    recipient_bal = await get_balance(session, recipient, chain, asset)

    sender_bal.amount -= amount
    recipient_bal.amount += amount

    out_tx = Transaction(
        user_id=sender.id,
        type=TxType.INTERNAL_OUT,
        status=TxStatus.CONFIRMED,
        chain=chain,
        asset=asset,
        amount=amount,
        counterparty_user_id=recipient.id,
        note=note,
    )
    in_tx = Transaction(
        user_id=recipient.id,
        type=TxType.INTERNAL_IN,
        status=TxStatus.CONFIRMED,
        chain=chain,
        asset=asset,
        amount=amount,
        counterparty_user_id=sender.id,
        note=note,
    )
    session.add_all([out_tx, in_tx])
    session.add(
        AuditLog(
            user_id=sender.id,
            event="internal_transfer",
            payload=f"to={recipient.id} {chain.value}:{asset.value}:{amount}",
        )
    )
    await session.flush()
    return out_tx, in_tx
