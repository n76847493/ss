"""Periodic deposit scanner.

For each active address, ask the chain adapter for incoming transfers
since we last checked and credit them to the user via
:func:`services.wallet.credit_deposit` (which is idempotent on txid).
"""
from __future__ import annotations

from sqlalchemy import select

from ..crypto.chains import OfflineError, get_adapter
from ..db.models import Address, User
from ..db.session import session_scope
from ..logging_setup import get_logger
from ..services.wallet import credit_deposit

log = get_logger("scanner")


async def scan_once() -> None:
    async with session_scope() as s:
        res = await s.execute(select(Address).where(Address.is_archived.is_(False)))
        addrs = res.scalars().all()

    for addr in addrs:
        try:
            adapter = get_adapter(addr.chain)
            incoming = await adapter.incoming_since(addr.address, addr.asset)
        except OfflineError:
            continue
        except Exception as e:  # noqa: BLE001
            log.warning("scanner.adapter_error", chain=addr.chain.value, addr=addr.address, err=str(e))
            continue

        if not incoming:
            continue

        async with session_scope() as s:
            user = (await s.execute(select(User).where(User.id == addr.user_id))).scalar_one()
            for tx in incoming:
                if tx.amount <= 0:
                    continue
                await credit_deposit(
                    s,
                    user,
                    chain=addr.chain,
                    asset=tx.asset,
                    amount=tx.amount,
                    txid=tx.txid,
                    address=addr.address,
                    counterparty=tx.counterparty,
                    confirmations=tx.confirmations,
                )
                log.info(
                    "deposit.credited",
                    user=user.id,
                    chain=addr.chain.value,
                    asset=tx.asset.value,
                    amount=str(tx.amount),
                    txid=tx.txid,
                )
