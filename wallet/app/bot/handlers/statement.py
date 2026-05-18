"""PDF/CSV statement export."""
from __future__ import annotations

from datetime import UTC, datetime, timedelta

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import BufferedInputFile, CallbackQuery, Message

from ...db.session import session_scope
from ...services.history import HistoryFilter, list_transactions
from ...services.statement import build_csv, build_pdf
from ...services.wallet import get_or_create_user
from ..keyboards import statement_kb

router = Router(name="statement")


@router.message(Command("statement"))
@router.message(F.text == "🧾 Выписка")
async def statement_menu(msg: Message) -> None:
    await msg.answer(
        "Выберите формат и период выписки. Файлы доставляются сразу в чат.",
        reply_markup=statement_kb(),
    )


@router.callback_query(F.data.startswith("stmt:"))
async def statement_make(cb: CallbackQuery) -> None:
    _, fmt, period = cb.data.split(":")
    date_from = None
    if period != "all":
        date_from = datetime.now(UTC) - timedelta(days=int(period))

    async with session_scope() as s:
        user = await get_or_create_user(s, telegram_id=cb.from_user.id)
        f = HistoryFilter(user_id=user.id, date_from=date_from, limit=10000)
        txs = await list_transactions(s, f)

    stamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    if fmt == "csv":
        data = build_csv(user, txs, f)
        await cb.message.answer_document(
            BufferedInputFile(data, filename=f"statement_{stamp}.csv"),
            caption=f"CSV-выписка ({len(txs)} операций).",
        )
    else:
        data = build_pdf(user, txs, f)
        await cb.message.answer_document(
            BufferedInputFile(data, filename=f"statement_{stamp}.pdf"),
            caption=f"PDF-выписка ({len(txs)} операций).",
        )
    await cb.answer("Готово")
