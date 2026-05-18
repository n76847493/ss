"""/start, /help, main menu, balance overview."""
from __future__ import annotations

from decimal import Decimal

from aiogram import F, Router
from aiogram.filters import Command, CommandStart
from aiogram.types import Message
from sqlalchemy import select

from ...db.models import Balance
from ...db.session import session_scope
from ...services.wallet import get_or_create_user
from ..keyboards import main_menu

router = Router(name="start")


WELCOME = (
    "<b>Кастодиальный кошелёк</b>\n\n"
    "Поддерживаемые активы: BTC, USDT (ERC-20/BEP-20/Polygon/TRC-20/TON), "
    "USDC (ERC-20/BEP-20/Polygon/TRC-20/Solana), TON.\n\n"
    "Команды:\n"
    "/start — открыть меню\n"
    "/help — справка\n"
    "/balance — текущий баланс\n"
    "/deposit — получить адрес для пополнения\n"
    "/withdraw — отправить на внешний адрес\n"
    "/transfer — внутренний перевод другому пользователю\n"
    "/history — история операций\n"
    "/statement — выписка (PDF/CSV)\n"
    "/settings — 2FA и прочее\n"
)


@router.message(CommandStart())
async def cmd_start(msg: Message) -> None:
    async with session_scope() as s:
        await get_or_create_user(
            s,
            telegram_id=msg.from_user.id,
            username=msg.from_user.username,
            first_name=msg.from_user.first_name,
        )
    await msg.answer(WELCOME, reply_markup=main_menu())


@router.message(Command("help"))
async def cmd_help(msg: Message) -> None:
    await msg.answer(WELCOME, reply_markup=main_menu())


@router.message(Command("balance"))
@router.message(F.text == "💰 Баланс")
async def cmd_balance(msg: Message) -> None:
    async with session_scope() as s:
        user = await get_or_create_user(
            s,
            telegram_id=msg.from_user.id,
            username=msg.from_user.username,
            first_name=msg.from_user.first_name,
        )
        res = await s.execute(select(Balance).where(Balance.user_id == user.id))
        balances = res.scalars().all()

    if not balances:
        await msg.answer("Баланс пуст. Пополните счёт через /deposit.", reply_markup=main_menu())
        return

    lines = ["<b>Текущий баланс</b>"]
    for b in balances:
        available = (b.amount or Decimal(0)) - (b.locked or Decimal(0))
        line = f"<code>{b.asset.value:<5}</code> {b.chain.value:<8} {available:.8f}"
        if b.locked and b.locked > 0:
            line += f"  (зарезервировано: {b.locked:.8f})"
        lines.append(line)
    await msg.answer("\n".join(lines), reply_markup=main_menu())
