"""Core wallet service: users, addresses, balances, deposit & withdrawal flows."""
from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..crypto.chains import get_adapter
from ..crypto.hd import derive
from ..db.models import (
    Address,
    Asset,
    AuditLog,
    Balance,
    Chain,
    Transaction,
    TxStatus,
    TxType,
    User,
    WithdrawalRequest,
)


async def get_or_create_user(
    session: AsyncSession,
    telegram_id: int,
    *,
    username: str | None = None,
    first_name: str | None = None,
) -> User:
    res = await session.execute(select(User).where(User.telegram_id == telegram_id))
    user = res.scalar_one_or_none()
    if user is None:
        user = User(telegram_id=telegram_id, username=username, first_name=first_name)
        session.add(user)
        await session.flush()
        session.add(AuditLog(user_id=user.id, event="user_created"))
    else:
        if username and user.username != username:
            user.username = username
        if first_name and user.first_name != first_name:
            user.first_name = first_name
    return user


async def issue_deposit_address(
    session: AsyncSession,
    user: User,
    chain: Chain,
    asset: Asset,
) -> Address:
    """Mint a fresh one-time deposit address for the user/chain/asset.

    This is the standard exchange pattern — a new derivation index per
    deposit makes attribution easy, lets the user rotate addresses, and
    has nothing to do with mixing/obfuscation: every address remains
    publicly traceable on-chain.
    """
    # determine next derivation index for this chain (global counter)
    res = await session.execute(
        select(Address.derivation_index)
        .where(Address.chain == chain)
        .order_by(Address.derivation_index.desc())
        .limit(1)
    )
    last = res.scalar_one_or_none()
    next_idx = (last + 1) if last is not None else 0

    derived = derive(chain, next_idx)
    addr = Address(
        user_id=user.id,
        chain=chain,
        asset=asset,
        derivation_index=next_idx,
        address=derived.address,
        is_active=True,
        last_used_at=datetime.now(UTC),
    )
    session.add(addr)
    session.add(
        AuditLog(
            user_id=user.id,
            event="address_issued",
            payload=f"{chain.value}:{asset.value}:{derived.address}",
        )
    )
    await session.flush()
    return addr


async def get_balance(session: AsyncSession, user: User, chain: Chain, asset: Asset) -> Balance:
    res = await session.execute(
        select(Balance).where(
            Balance.user_id == user.id, Balance.chain == chain, Balance.asset == asset
        )
    )
    bal = res.scalar_one_or_none()
    if bal is None:
        bal = Balance(user_id=user.id, chain=chain, asset=asset, amount=Decimal(0), locked=Decimal(0))
        session.add(bal)
        await session.flush()
    return bal


async def credit_deposit(
    session: AsyncSession,
    user: User,
    *,
    chain: Chain,
    asset: Asset,
    amount: Decimal,
    txid: str,
    address: str,
    counterparty: str | None,
    confirmations: int,
) -> Transaction:
    """Credit an incoming on-chain transfer to the user's internal balance.

    Idempotent on (txid, address, asset).
    """
    res = await session.execute(
        select(Transaction).where(
            Transaction.txid == txid,
            Transaction.address_to == address,
            Transaction.asset == asset,
            Transaction.type == TxType.DEPOSIT,
        )
    )
    existing = res.scalar_one_or_none()
    if existing is not None:
        existing.confirmations = max(existing.confirmations, confirmations)
        if confirmations > 0 and existing.status == TxStatus.PENDING:
            existing.status = TxStatus.CONFIRMED
        return existing

    bal = await get_balance(session, user, chain, asset)
    bal.amount = (bal.amount or Decimal(0)) + amount

    tx = Transaction(
        user_id=user.id,
        type=TxType.DEPOSIT,
        status=TxStatus.CONFIRMED if confirmations > 0 else TxStatus.PENDING,
        chain=chain,
        asset=asset,
        amount=amount,
        address_from=counterparty,
        address_to=address,
        txid=txid,
        confirmations=confirmations,
    )
    session.add(tx)
    session.add(
        AuditLog(
            user_id=user.id,
            event="deposit_credited",
            payload=f"{chain.value}:{asset.value}:{amount}:{txid}",
        )
    )
    return tx


async def request_withdrawal(
    session: AsyncSession,
    user: User,
    *,
    chain: Chain,
    asset: Asset,
    amount: Decimal,
    address: str,
) -> WithdrawalRequest:
    bal = await get_balance(session, user, chain, asset)
    if (bal.amount - bal.locked) < amount:
        raise ValueError("insufficient balance")

    bal.locked += amount
    req = WithdrawalRequest(
        user_id=user.id,
        chain=chain,
        asset=asset,
        amount=amount,
        address=address,
        status=TxStatus.PENDING,
    )
    session.add(req)
    session.add(
        AuditLog(
            user_id=user.id,
            event="withdrawal_requested",
            payload=f"{chain.value}:{asset.value}:{amount}:{address}",
        )
    )
    await session.flush()
    return req


async def finalize_withdrawal(
    session: AsyncSession,
    req: WithdrawalRequest,
    *,
    txid: str,
    fee: Decimal = Decimal(0),
) -> Transaction:
    user = (await session.execute(select(User).where(User.id == req.user_id))).scalar_one()
    bal = await get_balance(session, user, req.chain, req.asset)

    # debit funds
    bal.amount -= req.amount
    bal.locked = max(Decimal(0), bal.locked - req.amount)

    tx = Transaction(
        user_id=user.id,
        type=TxType.WITHDRAW,
        status=TxStatus.BROADCAST,
        chain=req.chain,
        asset=req.asset,
        amount=req.amount,
        fee=fee,
        address_to=req.address,
        txid=txid,
    )
    session.add(tx)
    req.status = TxStatus.BROADCAST
    req.transaction_id = tx.id
    session.add(
        AuditLog(
            user_id=user.id,
            event="withdrawal_broadcast",
            payload=f"{req.chain.value}:{req.asset.value}:{req.amount}:{txid}",
        )
    )
    return tx


async def cancel_withdrawal(session: AsyncSession, req: WithdrawalRequest) -> None:
    if req.status != TxStatus.PENDING:
        return
    user = (await session.execute(select(User).where(User.id == req.user_id))).scalar_one()
    bal = await get_balance(session, user, req.chain, req.asset)
    bal.locked = max(Decimal(0), bal.locked - req.amount)
    req.status = TxStatus.CANCELLED
    session.add(
        AuditLog(
            user_id=user.id,
            event="withdrawal_cancelled",
            payload=f"req_id={req.id}",
        )
    )


def chain_supports_online(chain: Chain) -> bool:
    """Quick check whether the adapter has online RPC configured."""
    adapter = get_adapter(chain)
    # OfflineAdapter doesn't inherit from anything special; detect by class name.
    return adapter.__class__.__name__ != "OfflineAdapter"
