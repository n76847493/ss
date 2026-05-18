"""Periodic withdrawal processor."""
from __future__ import annotations

from sqlalchemy import select

from ..crypto.chains import OfflineError, get_adapter
from ..crypto.hd import derive
from ..db.models import TxStatus, WithdrawalRequest
from ..db.session import session_scope
from ..logging_setup import get_logger
from ..services.wallet import cancel_withdrawal, finalize_withdrawal

log = get_logger("withdraw")


async def process_once() -> None:
    async with session_scope() as s:
        res = await s.execute(
            select(WithdrawalRequest).where(WithdrawalRequest.status == TxStatus.PENDING)
        )
        reqs = res.scalars().all()

    for req in reqs:
        adapter = get_adapter(req.chain)
        try:
            # The hot wallet is conventionally the operator's master derivation
            # index 0 — operators with cold/hot split should adapt this hook.
            hot_index = 0
            _ = derive(req.chain, hot_index)
            txid = await adapter.send(
                from_index=hot_index,
                to_address=req.address,
                asset=req.asset,
                amount=req.amount,
            )
        except (OfflineError, NotImplementedError) as e:
            log.info("withdrawal.deferred_to_admin", req=req.id, reason=str(e))
            # leave PENDING for admin approval in the panel
            continue
        except Exception as e:  # noqa: BLE001
            log.warning("withdrawal.failed", req=req.id, err=str(e))
            async with session_scope() as s:
                attached = await s.get(WithdrawalRequest, req.id)
                if attached:
                    await cancel_withdrawal(s, attached)
            continue

        async with session_scope() as s:
            attached = await s.get(WithdrawalRequest, req.id)
            if attached is None:
                continue
            await finalize_withdrawal(s, attached, txid=txid)
            log.info("withdrawal.broadcast", req=req.id, txid=txid)
