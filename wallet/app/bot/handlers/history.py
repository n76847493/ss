"""Transaction history viewer."""
from __future__ import annotations

from datetime import UTC, datetime, timedelta

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from ...db.models import Asset, Chain, TxType
from ...db.session import session_scope
from ...services.history import HistoryFilter, list_transactions
from ...services.wallet import get_or_create_user
from ..keyboards import history_filters_kb

router = Router(name="history")


@router.message(Command("history"))
@router.message(F.text == "📜 История")
async def history_open(msg: Message, state: FSMContext) -> None:
    await state.update_data(hist_type=None, hist_asset=None, hist_chain=None, hist_period=30)
    await _render(msg, state)


async def _render(msg_or_cb, state: FSMContext) -> None:
    data = await state.get_data()
    period = data.get("hist_period", 30)
    date_from = None if period == "all" else datetime.now(UTC) - timedelta(days=int(period))
    f = HistoryFilter(
        user_id=0,
        chain=Chain(data["hist_chain"]) if data.get("hist_chain") else None,
        asset=Asset(data["hist_asset"]) if data.get("hist_asset") else None,
        tx_type=TxType(data["hist_type"]) if data.get("hist_type") else None,
        date_from=date_from,
        limit=20,
    )
    async with session_scope() as s:
        user = await get_or_create_user(
            s, telegram_id=msg_or_cb.from_user.id, username=msg_or_cb.from_user.username
        )
        f.user_id = user.id
        txs = await list_transactions(s, f)

    if not txs:
        body = "Операций не найдено."
    else:
        lines = ["<b>История</b> (последние)"]
        for t in txs:
            sign = "+" if t.type.value in ("DEPOSIT", "INTERNAL_IN") else "−"
            lines.append(
                f"{t.created_at.strftime('%m-%d %H:%M')}  {t.type.value[:7]:7}  "
                f"{t.chain.value[:4]:4} {t.asset.value:5} {sign}{t.amount:.8f}"
            )
        body = "<pre>" + "\n".join(lines) + "</pre>"

    if isinstance(msg_or_cb, Message):
        await msg_or_cb.answer(body, reply_markup=history_filters_kb())
    else:
        await msg_or_cb.message.edit_text(body, reply_markup=history_filters_kb())


@router.callback_query(F.data.startswith("hist:type:"))
async def hist_type(cb: CallbackQuery, state: FSMContext) -> None:
    val = cb.data.split(":")[-1]
    await state.update_data(hist_type=None if val == "any" else val)
    await _render(cb, state)
    await cb.answer()


@router.callback_query(F.data.startswith("hist:asset:"))
async def hist_asset(cb: CallbackQuery, state: FSMContext) -> None:
    val = cb.data.split(":")[-1]
    await state.update_data(hist_asset=None if val == "any" else val)
    await _render(cb, state)
    await cb.answer()


@router.callback_query(F.data.startswith("hist:period:"))
async def hist_period(cb: CallbackQuery, state: FSMContext) -> None:
    val = cb.data.split(":")[-1]
    await state.update_data(hist_period=val if val == "all" else int(val))
    await _render(cb, state)
    await cb.answer()
